"""GET/POST/PUT/DELETE /api/investments/assets and /api/investments/movements,
plus portfolio aggregation and B3 file import with flexible column detection.

Investments module supports B3 (Brazilian stock exchange) portfolio tracking:
- Asset CRUD (ticker, type, name)
- Movement tracking (buys, sells, dividends, bonus shares, splits)
- Portfolio position aggregation (quantity held, average purchase price, total invested)
- Flexible B3 file import with column auto-detection and user confirmation flow
"""
import csv
import io
import logging
from datetime import date
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db

logger = logging.getLogger("app.investments")

router = APIRouter(
    prefix="/api/investments",
    tags=["investments"],
    dependencies=[Depends(get_current_user)],
)


# Column name synonyms for flexible B3 file import detection.
# Each key is a logical field name; the list contains variations of header strings
# we expect from a B3 export file (case-insensitive substring matching).
COLUMN_SYNONYMS = {
    "date": ["data", "data movimentação", "data do movimento", "data da operação", "data_mov", "data_operacao"],
    "movement_type": ["movimentação", "tipo de movimentação", "tipo", "natureza", "tipo_mov", "mov_type"],
    "ticker": ["produto", "ativo", "código de negociação", "papel", "codigo", "ticker", "symbol"],
    "quantity": ["quantidade", "qtde", "qtd", "quantidade_mov", "qtd_mov", "qty"],
    "unit_price": ["preço", "preço unitário", "valor unitário", "preço de tela", "preco", "unit_price", "price"],
    "total_value": ["valor", "valor total", "valor da operação", "valor operação", "valor_total", "total"],
    # Optional: B3's real "Movimentação" export has a separate Credito/Debito column
    # (confirmed against a real exported file) that's needed to disambiguate generic
    # "Transferência - Liquidação" rows into compra vs venda -- see _normalize_movement_type.
    "direction": ["entrada/saída", "entrada/saida", "e/s", "direção", "direcao", "tipo de lançamento"],
}

# Fields NOT required in a confirmed column_mapping -- "direction" is optional
# (only used to disambiguate ambiguous movement types when present).
OPTIONAL_MAPPING_FIELDS = {"unit_price", "total_value", "direction"}

# The exact header row of B3's own "Movimentação" export from the investor
# portal (investidor.b3.com.br -> Extratos e Informativos), confirmed against
# a real file the user provided. When a file's headers match this exactly
# (order-independent), we know the mapping with certainty and can skip
# asking the user to manually review/correct each column -- the synonym
# matching above still exists as the fallback for anything that doesn't
# match this precisely (other brokers, older exports, hand-edited files).
KNOWN_B3_MOVIMENTACAO_HEADERS = {
    "Entrada/Saída", "Data", "Movimentação", "Produto",
    "Instituição", "Quantidade", "Preço unitário", "Valor da Operação",
}


def _is_known_b3_format(headers: list[str]) -> bool:
    return {h.strip() for h in headers} == KNOWN_B3_MOVIMENTACAO_HEADERS


def _extract_ticker(raw_product: str) -> str:
    """Extract a bare ticker from a B3 "Produto" cell.

    Real B3 exports combine the ticker and the full company/fund name in one
    cell, e.g. "BBAS3 - BANCO DO BRASIL S/A" or "HGLG11 - PÁTRIA LOG - FDO INV
    IMOB - RESPONSABILIDADE LTDA." (confirmed against a real exported file --
    the ticker is always the first " - "-separated segment, even when the
    name itself contains more dashes).
    """
    return raw_product.split(" - ")[0].strip()


def _guess_asset_type(ticker: str) -> str:
    """Best-effort asset type from a B3 ticker's suffix.

    B3 ticker codes are (mostly) a short base code plus a trailing number --
    but the base code itself can contain digits too (e.g. "B3SA3", B3's own
    ticker), so this only constrains overall shape/length, not "letters
    only before the last digit". This is a heuristic, not authoritative --
    "outro" is the honest fallback whenever the ticker doesn't look like a
    standard B3 exchange code at all (e.g. "CDB" from "CDB - CDB3266WRKT -
    ITAU...", a fixed income product, not a ticker in this sense). The user
    can always correct the type manually afterward; this just saves them
    from having to do it for every single row when the guess is obvious.
    """
    t = ticker.strip().upper()

    # Check for fixed income products first (before length/format check,
    # since these often have longer names than standard ticker codes).
    if "TESOURO" in t:
        return "tesouro"
    if any(keyword in t for keyword in ("CDB", "LCI", "LCA", "CRI", "CRA", "DEBENTURE", "DEBÊNTURE", "POUPANCA", "POUPANÇA")):
        return "renda_fixa"

    # Standard ticker format check
    if len(t) not in (5, 6) or not t[0].isalpha():
        return "outro"
    # BDRs: ends in "34" (e.g. AAPL34, GOGL34) -- check before the generic
    # single-trailing-digit rule below, since that would also match "...4".
    if t.endswith("34"):
        return "bdr"
    # FIIs/ETFs: ends in "11" (e.g. HGLG11, BOVA11). Can't reliably tell FII
    # from ETF by suffix alone -- FII is the far more common case in
    # practice, so that's the default guess.
    if t.endswith("11"):
        return "fii"
    # Ordinary/preferred shares: ends in a single digit 1-8.
    if t[-1].isdigit() and t[-1] in "12345678":
        return "acao"
    return "outro"


def _detect_column(header: str, field: str) -> float:
    """Attempt fuzzy matching between a header string and synonyms for a field.

    Returns a confidence score (0.0-1.0) where 1.0 is an exact match.
    Uses case-insensitive substring matching plus SequenceMatcher ratio for partial matches.
    """
    header_lower = header.lower().strip()
    synonyms = COLUMN_SYNONYMS.get(field, [])

    max_score = 0.0
    for synonym in synonyms:
        synonym_lower = synonym.lower().strip()
        # Exact substring match: boost score
        if synonym_lower in header_lower or header_lower in synonym_lower:
            max_score = max(max_score, 0.95)
        # Fuzzy ratio as fallback
        max_score = max(max_score, SequenceMatcher(None, header_lower, synonym_lower).ratio())

    return max_score


def _detect_mapping(headers: list[str]) -> dict[str, Optional[str]]:
    """Auto-detect which column corresponds to each logical field.

    Returns a dict mapping field names to detected header names (or None if not
    confidently detected). Only returns headers with a confidence score >= 0.6.
    """
    mapping = {}
    for field in COLUMN_SYNONYMS.keys():
        best_header = None
        best_score = 0.0
        for header in headers:
            score = _detect_column(header, field)
            if score > best_score:
                best_score = score
                best_header = header
        # Only include if confidence is high enough
        mapping[field] = best_header if best_score >= 0.6 else None

    return mapping


def _parse_csv(file_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV file into headers and rows.

    Returns (headers, rows) where rows is a list of dicts mapping column names to values.
    """
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback to latin-1 for some Brazilian files
        text = file_bytes.decode("latin-1")

    reader = csv.reader(io.StringIO(text))
    headers = next(reader)
    rows = [dict(zip(headers, row)) for row in reader]
    return headers, rows


def _parse_xlsx(file_bytes: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse XLSX file into headers and rows.

    Returns (headers, rows) where rows is a list of dicts mapping column names to values.
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="openpyxl is not installed; cannot parse XLSX files",
        )

    workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    worksheet = workbook.active

    rows = []
    headers = None
    for idx, row in enumerate(worksheet.iter_rows(values_only=True), 1):
        if idx == 1:
            headers = [str(cell or "").strip() for cell in row]
        else:
            if all(cell is None or str(cell).strip() == "" for cell in row):
                break
            rows.append(dict(zip(headers, [str(cell or "") for cell in row])))

    return headers or [], rows


def _normalize_movement_type(raw_type: str, direction: Optional[str] = None) -> str:
    """Normalize movement type strings from B3 files to internal enum values.

    Handles common Portuguese variations case-insensitively. `direction`, if
    given, is the raw value of the "Entrada/Saída" (Credito/Debito) column --
    confirmed against a real B3 export, the dominant movement type there is
    "Transferência - Liquidação" (trade settlement), which by itself doesn't
    say whether it was a buy or a sell; Credito (shares/money in) means
    compra, Debito (shares/money out) means venda.
    """
    normalized = raw_type.strip().lower()
    direction_normalized = direction.strip().lower() if direction else None

    if normalized in ("compra", "buy", "compras"):
        return "compra"
    elif normalized in ("venda", "sell", "vendas"):
        return "venda"
    elif normalized in ("bonificação", "bonificacao", "bonus"):
        return "bonificacao"
    elif normalized in (
        "provento", "dividendo", "jcp", "rendimento", "dividend",
        "juros sobre capital próprio", "juros sobre capital proprio",
        "rendimento (juros)", "amortização", "amortizacao",
    ):
        return "provento"
    elif normalized in ("desdobramento", "split", "splitting"):
        return "desdobramento"
    elif "transferência" in normalized or "transferencia" in normalized or "liquidação" in normalized or "liquidacao" in normalized:
        # Generic settlement row -- only resolvable with the direction column.
        if direction_normalized in ("credito", "crédito"):
            return "compra"
        elif direction_normalized in ("debito", "débito"):
            return "venda"
        return "outro"
    else:
        return "outro"


# ========== Asset CRUD ==========
@router.get("/assets", response_model=list[schemas.AssetOut])
def list_assets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assets = crud.get_assets(db, current_user.id)
    return [schemas.AssetOut.model_validate(a, from_attributes=True) for a in assets]


@router.post("/assets", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset: schemas.AssetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_asset = crud.create_asset(db, current_user.id, asset)
    return schemas.AssetOut.model_validate(db_asset, from_attributes=True)


@router.put("/assets/{asset_id}", response_model=schemas.AssetOut)
def update_asset(
    asset_id: int,
    asset: schemas.AssetUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_asset = crud.get_asset(db, asset_id, current_user.id)
    if db_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    db_asset = crud.update_asset(db, db_asset, asset)
    return schemas.AssetOut.model_validate(db_asset, from_attributes=True)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_asset = crud.get_asset(db, asset_id, current_user.id)
    if db_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    crud.delete_asset(db, db_asset)


# ========== Investment Movement CRUD ==========
@router.get("/movements", response_model=list[schemas.InvestmentMovementOut])
def list_movements(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    movements = crud.get_investment_movements(db, current_user.id)
    return [schemas.InvestmentMovementOut.model_validate(m, from_attributes=True) for m in movements]


@router.post("/movements", response_model=schemas.InvestmentMovementOut, status_code=status.HTTP_201_CREATED)
def create_movement(
    movement: schemas.InvestmentMovementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify asset belongs to current user
    asset = crud.get_asset(db, movement.asset_id, current_user.id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    db_movement = crud.create_investment_movement(db, current_user.id, movement)
    return schemas.InvestmentMovementOut.model_validate(db_movement, from_attributes=True)


@router.put("/movements/{movement_id}", response_model=schemas.InvestmentMovementOut)
def update_movement(
    movement_id: int,
    movement: schemas.InvestmentMovementUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_movement = crud.get_investment_movement(db, movement_id, current_user.id)
    if db_movement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")

    # Verify asset belongs to current user (if changed)
    if movement.asset_id is not None and movement.asset_id != db_movement.asset_id:
        asset = crud.get_asset(db, movement.asset_id, current_user.id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    db_movement = crud.update_investment_movement(db, db_movement, movement)
    return schemas.InvestmentMovementOut.model_validate(db_movement, from_attributes=True)


@router.delete("/movements/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movement(
    movement_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_movement = crud.get_investment_movement(db, movement_id, current_user.id)
    if db_movement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    crud.delete_investment_movement(db, db_movement)


# ========== Portfolio Aggregation ==========
@router.get("/portfolio", response_model=list[schemas.PortfolioPositionOut])
def get_portfolio(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_portfolio(db, current_user.id)


# ========== Position History (Snapshots) ==========
@router.get("/positions/history", response_model=list[schemas.PositionSnapshotOut] | list[schemas.ConsolidatedPositionOut])
def get_position_history(
    asset_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get position history over time.

    If asset_id is provided: return snapshots for that asset (404 if not owned by user).
    If asset_id is omitted: return consolidated (summed) invested value per date across all assets.
    The consolidation uses a carry-forward approach: for dates where an asset has no snapshot,
    its last known position is carried forward (or 0 if no previous snapshot exists).
    """
    if asset_id is not None:
        # Single asset: verify it belongs to the user
        asset = crud.get_asset(db, asset_id, current_user.id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        snapshots = crud.get_position_snapshots_for_asset(db, asset_id, current_user.id)
        return [
            schemas.PositionSnapshotOut(
                date=s.date,
                asset_id=s.asset_id,
                quantity_held=s.quantity_held,
                invested_value=s.invested_value,
            )
            for s in snapshots
        ]
    else:
        # Consolidated: merge snapshots from all assets, carrying forward last-known values per asset
        all_snapshots = crud.get_position_snapshots_for_user(db, current_user.id)

        if not all_snapshots:
            return []

        # Build a map of (asset_id -> list of snapshots sorted by date)
        snapshots_by_asset: dict[int, list[models.InvestmentPositionSnapshot]] = {}
        all_dates = set()
        for snapshot in all_snapshots:
            if snapshot.asset_id not in snapshots_by_asset:
                snapshots_by_asset[snapshot.asset_id] = []
            snapshots_by_asset[snapshot.asset_id].append(snapshot)
            all_dates.add(snapshot.date)

        # For each date, compute total invested value by carrying forward last-known values
        # for each asset (or 0 if no previous snapshot exists for that asset).
        # Approach: for each date in sorted order, for each asset, find its latest snapshot
        # on or before that date.
        result_by_date: dict[date, float] = {}

        for current_date in sorted(all_dates):
            total_invested = 0.0
            for asset_id, snapshots_for_asset in snapshots_by_asset.items():
                # Find the latest snapshot on or before current_date
                latest_value = 0.0
                for snapshot in snapshots_for_asset:
                    if snapshot.date <= current_date:
                        latest_value = snapshot.invested_value
                    else:
                        break
                total_invested += latest_value

            result_by_date[current_date] = total_invested

        return [
            schemas.ConsolidatedPositionOut(date=d, total_invested_value=v)
            for d, v in sorted(result_by_date.items())
        ]


# ========== B3 File Import ==========
@router.post("/import")
def import_b3_file(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import a B3 export file (CSV or XLSX).

    Two-phase workflow:
    1. If column_mapping is NOT provided: return a preview with auto-detected columns
       and sample rows for user confirmation.
    2. If column_mapping IS provided: user has confirmed/corrected the mapping;
       commit all movements and assets to the database.

    column_mapping, if provided, should be a JSON string:
      {"date": "Data da Operação", "movement_type": "Tipo", "ticker": "Produto", ...}
    """
    import json

    # Read file
    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File is empty",
        )

    # Parse based on file extension
    if file.filename.endswith(".xlsx"):
        try:
            headers, rows = _parse_xlsx(file_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse XLSX file: {str(e)}",
            )
    elif file.filename.endswith(".csv"):
        try:
            headers, rows = _parse_csv(file_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to parse CSV file: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be CSV or XLSX",
        )

    # If no mapping provided: return preview
    if not column_mapping:
        detected_mapping = _detect_mapping(headers)
        sample_rows = [
            {k: row.get(k, None) for k in headers}
            for row in rows[:5]
        ]
        return schemas.ImportPreviewResponse(
            committed=False,
            raw_columns=headers,
            detected_mapping=detected_mapping,
            sample_rows=sample_rows,
            row_count=len(rows),
            is_known_b3_format=_is_known_b3_format(headers),
        )

    # Parse the provided mapping
    try:
        mapping = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="column_mapping must be valid JSON",
        )

    # Validate required fields
    required_fields = {"date", "ticker", "movement_type"}
    if not all(mapping.get(field) for field in required_fields):
        missing = [f for f in required_fields if not mapping.get(f)]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required columns in mapping: {', '.join(missing)}",
        )

    # Process each row: create asset if needed, then create movement
    assets_created = 0
    movements_created = 0
    # Track assets affected by this import so we can rebuild their snapshots
    affected_asset_ids = set()

    for row in rows:
        # Extract mapped values
        try:
            raw_date = row.get(mapping["date"], "").strip()
            raw_product = row.get(mapping["ticker"], "").strip()
            raw_movement_type = row.get(mapping["movement_type"], "").strip()
            raw_quantity = row.get(mapping.get("quantity"), "").strip()
            raw_unit_price = row.get(mapping.get("unit_price"), "").strip()
            raw_total_value = row.get(mapping.get("total_value"), "").strip()
            raw_direction = row.get(mapping.get("direction"), "").strip()

            # Validate required values
            if not raw_date or not raw_product or not raw_movement_type:
                continue

            raw_ticker = _extract_ticker(raw_product)
            if not raw_ticker:
                continue

            # Parse date
            try:
                movement_date = date.fromisoformat(raw_date)
            except ValueError:
                # Try DD/MM/YYYY format common in Brazil
                try:
                    parts = raw_date.split("/")
                    if len(parts) == 3:
                        movement_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                    else:
                        continue
                except (ValueError, IndexError):
                    continue

            # Normalize movement type first (before validation)
            normalized_type = _normalize_movement_type(raw_movement_type, raw_direction or None)

            # Parse quantity and prices
            try:
                quantity = float(raw_quantity.replace(",", ".")) if raw_quantity else 0.0
                unit_price_val = float(raw_unit_price.replace(",", ".")) if raw_unit_price else None
                total_value = float(raw_total_value.replace(",", ".")) if raw_total_value else 0.0
            except ValueError:
                continue

            if quantity <= 0:
                continue

            # For non-purchase movements, unit_price is irrelevant; set to None if 0
            if normalized_type != "compra" and unit_price_val == 0.0:
                unit_price_val = None

            # For non-purchase movements (bonuses, splits, dividends), total_value can be 0
            if normalized_type == "compra" and total_value <= 0:
                continue
            if total_value < 0:
                continue

            # Get or create asset, guessing asset_type from the ticker suffix
            # (see _guess_asset_type) -- best-effort, user-correctable.
            asset = crud.get_asset_by_ticker(db, current_user.id, raw_ticker)
            if asset is None:
                asset = crud.create_asset(
                    db,
                    current_user.id,
                    schemas.AssetCreate(
                        ticker=raw_ticker, name=None, asset_type=_guess_asset_type(raw_ticker)
                    ),
                )
                assets_created += 1

            affected_asset_ids.add(asset.id)

            # Create movement (this will trigger a rebuild for this asset)
            crud.create_investment_movement(
                db,
                current_user.id,
                schemas.InvestmentMovementCreate(
                    asset_id=asset.id,
                    date=movement_date,
                    movement_type=normalized_type,
                    quantity=quantity,
                    unit_price=unit_price_val,
                    total_value=total_value,
                ),
            )
            movements_created += 1

        except Exception:
            logger.exception("Skipping malformed B3 import row: %r", row)
            continue

    return schemas.ImportCommitResponse(
        committed=True,
        assets_created=assets_created,
        movements_created=movements_created,
    )
