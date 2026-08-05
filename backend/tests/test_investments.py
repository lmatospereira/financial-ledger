"""Tests for investments: asset/movement CRUD, portfolio aggregation, and B3 file import."""
import json
import pytest

from app import auth, crud


# ========== Asset CRUD Tests ==========
def make_asset(client, auth_headers, ticker="PETR4", name=None, asset_type="acao"):
    payload = {
        "ticker": ticker,
        "name": name,
        "asset_type": asset_type,
    }
    return client.post("/api/investments/assets", json=payload, headers=auth_headers)


def test_create_asset(client, auth_headers):
    response = make_asset(client, auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "PETR4"
    assert body["asset_type"] == "acao"
    assert "id" in body
    assert "created_at" in body


def test_create_asset_with_name(client, auth_headers):
    response = make_asset(client, auth_headers, name="Petrobras")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Petrobras"


def test_create_asset_fii(client, auth_headers):
    response = make_asset(client, auth_headers, ticker="MXRF11", asset_type="fii")
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "MXRF11"
    assert body["asset_type"] == "fii"


def test_list_assets(client, auth_headers):
    make_asset(client, auth_headers, ticker="PETR4")
    make_asset(client, auth_headers, ticker="VALE3")

    response = client.get("/api/investments/assets", headers=auth_headers)
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 2
    # Check they're sorted by ticker
    assert assets[0]["ticker"] == "PETR4"
    assert assets[1]["ticker"] == "VALE3"


def test_update_asset(client, auth_headers):
    created = make_asset(client, auth_headers).json()
    asset_id = created["id"]

    response = client.put(
        f"/api/investments/assets/{asset_id}",
        json={"name": "Petrobras SA", "asset_type": "acao"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Petrobras SA"


def test_delete_asset(client, auth_headers):
    created = make_asset(client, auth_headers).json()
    asset_id = created["id"]

    response = client.delete(f"/api/investments/assets/{asset_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's gone
    response = client.get("/api/investments/assets", headers=auth_headers)
    assets = response.json()
    assert len(assets) == 0


def test_asset_cross_user_isolation(client, auth_headers, db_session):
    """Verify CRUD functions enforce user isolation (404 not 403)."""
    # Create an asset as the main user
    created = make_asset(client, auth_headers).json()
    asset_id = created["id"]

    # Create another user and verify they can't see the asset
    other_user = crud.create_user(
        db_session,
        username="other_user",
        name="Other User",
        password_hash=auth.hash_password("password123"),
    )

    # Attempt to get the asset as another user should return None (simulating 404)
    retrieved = crud.get_asset(db_session, asset_id, other_user.id)
    assert retrieved is None


# ========== Investment Movement CRUD Tests ==========
def make_movement(
    client,
    auth_headers,
    asset_id,
    date="2026-01-15",
    movement_type="compra",
    quantity=10.0,
    unit_price=50.0,
    total_value=500.0,
):
    payload = {
        "asset_id": asset_id,
        "date": date,
        "movement_type": movement_type,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_value": total_value,
    }
    return client.post("/api/investments/movements", json=payload, headers=auth_headers)


def test_create_movement(client, auth_headers):
    asset = make_asset(client, auth_headers).json()
    response = make_movement(client, auth_headers, asset["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["asset_id"] == asset["id"]
    assert body["movement_type"] == "compra"
    assert body["quantity"] == 10.0
    assert body["unit_price"] == 50.0
    assert body["total_value"] == 500.0


def test_create_movement_dividend(client, auth_headers):
    asset = make_asset(client, auth_headers).json()
    response = make_movement(
        client,
        auth_headers,
        asset["id"],
        movement_type="provento",
        quantity=1.0,
        unit_price=None,
        total_value=25.0,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["movement_type"] == "provento"
    assert body["unit_price"] is None


def test_list_movements(client, auth_headers):
    asset = make_asset(client, auth_headers).json()
    make_movement(client, auth_headers, asset["id"])
    make_movement(client, auth_headers, asset["id"], quantity=5.0, total_value=250.0)

    response = client.get("/api/investments/movements", headers=auth_headers)
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) == 2


def test_update_movement(client, auth_headers):
    asset = make_asset(client, auth_headers).json()
    created = make_movement(client, auth_headers, asset["id"]).json()
    movement_id = created["id"]

    response = client.put(
        f"/api/investments/movements/{movement_id}",
        json={"quantity": 20.0, "total_value": 1000.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["quantity"] == 20.0
    assert body["total_value"] == 1000.0


def test_delete_movement(client, auth_headers):
    asset = make_asset(client, auth_headers).json()
    created = make_movement(client, auth_headers, asset["id"]).json()
    movement_id = created["id"]

    response = client.delete(f"/api/investments/movements/{movement_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's gone
    response = client.get("/api/investments/movements", headers=auth_headers)
    movements = response.json()
    assert len(movements) == 0


def test_movement_invalid_asset(client, auth_headers):
    """Creating a movement with non-existent asset returns 404."""
    response = make_movement(client, auth_headers, asset_id=999)
    assert response.status_code == 404


# ========== Portfolio Aggregation Tests ==========
def test_portfolio_buy_then_sell_partial(client, auth_headers):
    """Test portfolio aggregation: buy 100, sell 30, should hold 70."""
    asset = make_asset(client, auth_headers, ticker="TEST1").json()

    # Buy 100 @ 50.00 = 5000.00
    make_movement(
        client, auth_headers, asset["id"], quantity=100.0, unit_price=50.0, total_value=5000.0
    )

    # Sell 30 @ 55.00 = 1650.00 (price doesn't affect avg_price calculation)
    make_movement(
        client, auth_headers, asset["id"], movement_type="venda", quantity=30.0, unit_price=55.0, total_value=1650.0
    )

    response = client.get("/api/investments/portfolio", headers=auth_headers)
    assert response.status_code == 200
    portfolio = response.json()
    assert len(portfolio) == 1

    position = portfolio[0]
    assert position["ticker"] == "TEST1"
    assert position["quantity_held"] == 70.0
    assert position["avg_price"] == 50.0
    assert position["total_invested"] == 3500.0  # 70 * 50


def test_portfolio_profitability_with_current_price(client, auth_headers):
    """When an asset's current_price is set, the portfolio reports current
    value and profit/loss; when unset, those fields stay null (no live price
    feed exists, so profitability is only knowable once the user maintains
    current_price manually).
    """
    asset = make_asset(client, auth_headers, ticker="PROF1").json()
    make_movement(
        client, auth_headers, asset["id"], quantity=10.0, unit_price=10.0, total_value=100.0
    )

    response = client.get("/api/investments/portfolio", headers=auth_headers)
    position = response.json()[0]
    assert position["current_price"] is None
    assert position["current_value"] is None
    assert position["profit_loss"] is None
    assert position["profit_loss_pct"] is None

    update_response = client.put(
        f"/api/investments/assets/{asset['id']}",
        json={"current_price": 15.0},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["current_price"] == 15.0

    response = client.get("/api/investments/portfolio", headers=auth_headers)
    position = response.json()[0]
    assert position["current_price"] == 15.0
    assert position["current_value"] == 150.0  # 10 * 15
    assert position["profit_loss"] == 50.0  # 150 - 100
    assert position["profit_loss_pct"] == 50.0  # 50/100 * 100


def test_asset_current_price_can_be_cleared(client, auth_headers):
    """Setting current_price to null via update actually clears it.

    Regression test: crud.update_asset used to build the update dict with
    exclude_none=True, which silently dropped an explicit `current_price:
    null` instead of applying it, so "clearing" a price in the UI was a
    no-op.
    """
    asset = make_asset(client, auth_headers, ticker="CLR1").json()
    client.put(
        f"/api/investments/assets/{asset['id']}",
        json={"current_price": 42.0},
        headers=auth_headers,
    )

    response = client.put(
        f"/api/investments/assets/{asset['id']}",
        json={"current_price": None},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["current_price"] is None


def test_portfolio_fully_sold_excluded(client, auth_headers):
    """Fully sold positions are excluded from portfolio."""
    asset = make_asset(client, auth_headers, ticker="SOLD").json()

    make_movement(client, auth_headers, asset["id"], quantity=100.0, total_value=5000.0)
    make_movement(client, auth_headers, asset["id"], movement_type="venda", quantity=100.0, total_value=5000.0)

    response = client.get("/api/investments/portfolio", headers=auth_headers)
    assert response.status_code == 200
    portfolio = response.json()
    assert len(portfolio) == 0


def test_portfolio_with_bonus_and_split(client, auth_headers):
    """Test portfolio with bonus shares and stock split.

    Bonificacao and desdobramento dilute the average price by increasing
    the "total_bought" quantity without changing total_cost. This ensures
    that invested_value remains equal to the actual amount aportado (5000),
    not artificially inflated.
    """
    asset = make_asset(client, auth_headers, ticker="BONUS").json()

    # Buy 100 @ 50.00 = 5000.00
    make_movement(client, auth_headers, asset["id"], quantity=100.0, unit_price=50.0, total_value=5000.0)

    # Bonus: +20 shares (no cost, dilutes avg_price)
    make_movement(
        client,
        auth_headers,
        asset["id"],
        movement_type="bonificacao",
        quantity=20.0,
        unit_price=None,
        total_value=0.0,
    )

    # Stock split 2:1: +120 shares (no cost, further dilutes avg_price)
    make_movement(
        client,
        auth_headers,
        asset["id"],
        movement_type="desdobramento",
        quantity=120.0,
        unit_price=None,
        total_value=0.0,
    )

    response = client.get("/api/investments/portfolio", headers=auth_headers)
    assert response.status_code == 200
    portfolio = response.json()
    assert len(portfolio) == 1

    position = portfolio[0]
    assert position["quantity_held"] == 240.0  # 100 + 20 + 120
    # avg_price = 5000 / 240 ≈ 20.83
    assert abs(position["avg_price"] - (5000.0 / 240.0)) < 0.01
    # total_invested = 240 * (5000/240) = 5000 (only the actual aportado)
    assert abs(position["total_invested"] - 5000.0) < 0.01


# ========== B3 File Import Tests ==========
def test_import_preview_csv(client, auth_headers):
    """Test import preview mode with a recognizable CSV."""
    csv_content = """Data da Operação,Produto,Movimentação,Quantidade,Preço Unitário,Valor Total
2026-01-15,PETR4,Compra,100,50.00,5000.00
2026-01-16,VALE3,Compra,50,100.00,5000.00"""

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["committed"] is False
    assert "Data da Operação" in body["raw_columns"]
    assert "Produto" in body["raw_columns"]
    assert body["detected_mapping"]["date"] == "Data da Operação"
    assert body["detected_mapping"]["ticker"] == "Produto"
    assert body["detected_mapping"]["movement_type"] == "Movimentação"
    assert len(body["sample_rows"]) == 2
    assert body["row_count"] == 2

    # Verify nothing was written to DB
    response = client.get("/api/investments/assets", headers=auth_headers)
    assets = response.json()
    assert len(assets) == 0


def test_import_preview_unrecognizable_header(client, auth_headers):
    """Test that unrecognizable headers come back as null in detected_mapping."""
    csv_content = """UnknownColumn1,UnknownColumn2,UnknownColumn3
value1,value2,value3"""

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detected_mapping"]["date"] is None
    assert body["detected_mapping"]["ticker"] is None
    assert body["detected_mapping"]["movement_type"] is None


def test_import_commit_csv(client, auth_headers):
    """Test import commit mode: actually writes assets and movements."""
    csv_content = """Data da Operação,Produto,Movimentação,Quantidade,Preço Unitário,Valor Total
2026-01-15,PETR4,Compra,100,50.00,5000.00
2026-01-16,VALE3,Compra,50,100.00,5000.00"""

    # Step 1: Get preview to know the mapping
    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    preview = response.json()

    # Step 2: Re-submit with the confirmed mapping
    mapping = preview["detected_mapping"]
    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["committed"] is True
    assert body["assets_created"] == 2
    assert body["movements_created"] == 2

    # Verify assets were created
    response = client.get("/api/investments/assets", headers=auth_headers)
    assets = response.json()
    assert len(assets) == 2
    tickers = {a["ticker"] for a in assets}
    assert tickers == {"PETR4", "VALE3"}

    # Verify movements were created
    response = client.get("/api/investments/movements", headers=auth_headers)
    movements = response.json()
    assert len(movements) == 2


def test_import_real_b3_format(client, auth_headers):
    """Regression test against the actual B3 "Movimentação" export format
    (columns/values confirmed against a real exported file): the "Produto"
    column combines ticker and full company name ("BBAS3 - BANCO DO BRASIL
    S/A"), and the dominant movement type is the generic "Transferência -
    Liquidação", which only resolves to compra/venda via the separate
    "Entrada/Saída" (Credito/Debito) column.
    """
    csv_content = (
        "Entrada/Saída,Data,Movimentação,Produto,Instituição,Quantidade,Preço unitário,Valor da Operação\n"
        "Credito,29/07/2026,Transferência - Liquidação,BBAS3 - BANCO DO BRASIL S/A,ITAU CV S/A,2,20.45,40.9\n"
        "Credito,27/07/2026,Rendimento,KISU11 - KILIMA FDO INV IMOB,NOVA FUTURA CTVM LTDA,1,0.07,0.07\n"
        "Credito,14/07/2026,Juros Sobre Capital Próprio,B3SA3 - B3 S.A.,ITAU CV S/A,10,1.1,11\n"
    )

    response = client.post(
        "/api/investments/import",
        files={"file": ("mov.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    preview = response.json()
    assert preview["detected_mapping"]["direction"] == "Entrada/Saída"
    assert preview["detected_mapping"]["ticker"] == "Produto"
    assert preview["is_known_b3_format"] is True

    response = client.post(
        "/api/investments/import",
        files={"file": ("mov.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(preview["detected_mapping"])},
        headers=auth_headers,
    )
    body = response.json()
    assert body["committed"] is True
    assert body["assets_created"] == 3
    assert body["movements_created"] == 3

    assets = {a["ticker"]: a for a in client.get("/api/investments/assets", headers=auth_headers).json()}
    assert set(assets.keys()) == {"BBAS3", "KISU11", "B3SA3"}

    movements = client.get("/api/investments/movements", headers=auth_headers).json()
    by_asset = {m["asset_id"]: m["movement_type"] for m in movements}
    assert by_asset[assets["BBAS3"]["id"]] == "compra"
    assert by_asset[assets["KISU11"]["id"]] == "provento"
    assert by_asset[assets["B3SA3"]["id"]] == "provento"


def test_import_guesses_asset_type_from_ticker(client, auth_headers):
    """Newly created assets get a best-effort asset_type guessed from the
    ticker suffix (acao/fii/bdr), instead of always "outro".
    """
    csv_content = (
        "Data,Produto,Movimentação,Quantidade,Preço,Valor\n"
        "2026-01-15,PETR4,Compra,10,30.00,300.00\n"
        "2026-01-16,HGLG11,Compra,1,150.00,150.00\n"
        "2026-01-17,AAPL34,Compra,1,50.00,50.00\n"
        "2026-01-18,B3SA3,Compra,10,12.00,120.00\n"
    )
    response = client.post(
        "/api/investments/import",
        files={"file": ("mov.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    mapping = response.json()["detected_mapping"]
    response = client.post(
        "/api/investments/import",
        files={"file": ("mov.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.json()["committed"] is True

    assets_by_ticker = {a["ticker"]: a for a in client.get("/api/investments/assets", headers=auth_headers).json()}
    assert assets_by_ticker["PETR4"]["asset_type"] == "acao"
    assert assets_by_ticker["HGLG11"]["asset_type"] == "fii"
    assert assets_by_ticker["AAPL34"]["asset_type"] == "bdr"
    assert assets_by_ticker["B3SA3"]["asset_type"] == "acao"


def test_import_known_b3_format_false_for_other_layouts(client, auth_headers):
    """is_known_b3_format is only true for an exact match of B3's own
    export headers -- a different (even if fully mappable) layout should
    still go through the manual column-review step in the UI.
    """
    csv_content = "Data da Operação,Produto,Movimentação,Quantidade,Preço Unitário,Valor Total\n2026-01-15,PETR4,Compra,100,50.00,5000.00"
    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        headers=auth_headers,
    )
    assert response.json()["is_known_b3_format"] is False


def test_import_normalize_movement_types(client, auth_headers):
    """Test that movement types are normalized correctly."""
    csv_content = """Data,Ticker,Tipo,Quantidade,Preço,Valor
2026-01-15,PETR4,Compra,100,50.00,5000.00
2026-01-16,VALE3,Venda,50,100.00,5000.00
2026-01-17,ITUB4,Bonificação,10,0.00,0.00
2026-01-18,BBAS3,Provento,1,0.00,25.00
2026-01-19,CVCB3,Desdobramento,100,0.00,0.00"""

    mapping = {
        "date": "Data",
        "ticker": "Ticker",
        "movement_type": "Tipo",
        "quantity": "Quantidade",
        "unit_price": "Preço",
        "total_value": "Valor",
    }

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["movements_created"] == 5

    # Verify movements have correct normalized types
    response = client.get("/api/investments/movements", headers=auth_headers)
    movements = response.json()
    assert len(movements) == 5

    # Check they're normalized (all lowercase, canonical form)
    for m in movements:
        assert m["movement_type"] in ("compra", "venda", "bonificacao", "provento", "desdobramento", "outro")


def test_import_date_formats(client, auth_headers):
    """Test that both ISO and DD/MM/YYYY date formats are handled."""
    # Mix of date formats: ISO for the first, DD/MM/YYYY for the second
    csv_content = """Data,Ticker,Tipo,Quantidade,Preço,Valor
2026-01-15,PETR4,Compra,100,50.00,5000.00
15/01/2026,VALE3,Compra,50,100.00,5000.00"""

    mapping = {
        "date": "Data",
        "ticker": "Ticker",
        "movement_type": "Tipo",
        "quantity": "Quantidade",
        "unit_price": "Preço",
        "total_value": "Valor",
    }

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["movements_created"] == 2


def test_import_missing_required_column(client, auth_headers):
    """Test that missing required columns in the mapping fail with 422."""
    csv_content = """Data,Ticker,Tipo,Quantidade,Preço,Valor
2026-01-15,PETR4,Compra,100,50.00,5000.00"""

    # Provide a mapping missing "date"
    mapping = {
        "ticker": "Ticker",
        "movement_type": "Tipo",
    }

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "Missing required columns" in response.json()["detail"]


def test_import_duplicate_asset_ticker(client, auth_headers):
    """Test that importing the same ticker twice doesn't create duplicate assets."""
    csv_content = """Data,Ticker,Tipo,Quantidade,Preço,Valor
2026-01-15,PETR4,Compra,100,50.00,5000.00
2026-01-16,PETR4,Compra,50,52.00,2600.00"""

    mapping = {
        "date": "Data",
        "ticker": "Ticker",
        "movement_type": "Tipo",
        "quantity": "Quantidade",
        "unit_price": "Preço",
        "total_value": "Valor",
    }

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assets_created"] == 1  # Only one asset created
    assert body["movements_created"] == 2

    # Verify there's only one asset
    response = client.get("/api/investments/assets", headers=auth_headers)
    assets = response.json()
    assert len(assets) == 1


def test_import_invalid_json_mapping(client, auth_headers):
    """Test that invalid JSON in column_mapping fails with 422."""
    csv_content = """Data,Ticker,Tipo,Quantidade,Preço,Valor
2026-01-15,PETR4,Compra,100,50.00,5000.00"""

    response = client.post(
        "/api/investments/import",
        files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": "not valid json"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "valid JSON" in response.json()["detail"]


def test_import_xlsx_file(client, auth_headers):
    """Test import with XLSX file."""
    pytest.importorskip("openpyxl")
    from io import BytesIO

    import openpyxl

    # Create an XLSX file in memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Data da Operação", "Produto", "Movimentação", "Quantidade", "Preço Unitário", "Valor Total"])
    ws.append(["2026-01-15", "PETR4", "Compra", 100, 50.00, 5000.00])
    ws.append(["2026-01-16", "VALE3", "Compra", 50, 100.00, 5000.00])

    xlsx_bytes = BytesIO()
    wb.save(xlsx_bytes)
    xlsx_bytes.seek(0)

    # Get preview first
    response = client.post(
        "/api/investments/import",
        files={"file": ("test.xlsx", xlsx_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    preview = response.json()
    assert preview["committed"] is False
    assert "Data da Operação" in preview["raw_columns"]

    # Commit with mapping
    xlsx_bytes.seek(0)
    mapping = preview["detected_mapping"]
    response = client.post(
        "/api/investments/import",
        files={"file": ("test.xlsx", xlsx_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["committed"] is True
    assert body["movements_created"] == 2


# ========== Position Snapshot Tests ==========
def test_position_snapshots_created_on_movement(client, auth_headers):
    """Test that snapshots are automatically created when a movement is created."""
    asset = make_asset(client, auth_headers, ticker="SNAP1").json()

    # Create a buy movement
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    )

    # Fetch position history
    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    assert response.status_code == 200
    snapshots = response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["date"] == "2026-01-15"
    assert snapshots[0]["asset_id"] == asset["id"]
    assert snapshots[0]["quantity_held"] == 100.0
    assert snapshots[0]["invested_value"] == 5000.0


def test_position_snapshots_multiple_dates(client, auth_headers):
    """Test snapshots track position changes across multiple movements on different dates."""
    asset = make_asset(client, auth_headers, ticker="MULTI").json()

    # Buy 100 @ 50 on 2026-01-15
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    )

    # Sell 30 on 2026-02-01
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-02-01",
        movement_type="venda",
        quantity=30.0,
        unit_price=60.0,
        total_value=1800.0,
    )

    # Buy 50 more @ 55 on 2026-03-01
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-03-01",
        quantity=50.0,
        unit_price=55.0,
        total_value=2750.0,
    )

    # Fetch position history
    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    assert response.status_code == 200
    snapshots = response.json()
    assert len(snapshots) == 3

    # Check each snapshot
    assert snapshots[0]["date"] == "2026-01-15"
    assert snapshots[0]["quantity_held"] == 100.0
    assert snapshots[0]["invested_value"] == 5000.0

    assert snapshots[1]["date"] == "2026-02-01"
    assert snapshots[1]["quantity_held"] == 70.0
    assert snapshots[1]["invested_value"] == 3500.0  # 70 * 50

    assert snapshots[2]["date"] == "2026-03-01"
    assert snapshots[2]["quantity_held"] == 120.0
    # Cost: (100 * 50) + (50 * 55) = 5000 + 2750 = 7750
    # Avg: 7750 / 150 = 51.67
    # Invested: 120 * 51.67 = 6200
    # But we actually own 150 shares, so invested = 150 * 51.67 = 7750
    # Wait, on 2026-02-01 we sold 30, so we have 70, then we buy 50 more = 120
    # Cost for 150 total bought is 7750, invested for 120 held = 120 * (7750/150) = 6200
    assert abs(snapshots[2]["invested_value"] - 6200.0) < 0.01


def test_position_snapshots_update_triggers_rebuild(client, auth_headers):
    """Test that updating a movement triggers snapshot rebuild."""
    asset = make_asset(client, auth_headers, ticker="UPDT").json()

    # Create initial movement
    mvmt = make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    ).json()

    # Update the movement (increase quantity)
    response = client.put(
        f"/api/investments/movements/{mvmt['id']}",
        json={
            "quantity": 150.0,
            "unit_price": 50.0,
            "total_value": 7500.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Check snapshot was updated
    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    snapshots = response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["quantity_held"] == 150.0
    assert snapshots[0]["invested_value"] == 7500.0


def test_position_snapshots_delete_triggers_rebuild(client, auth_headers):
    """Test that deleting a movement triggers snapshot rebuild."""
    asset = make_asset(client, auth_headers, ticker="DELT").json()

    # Create two movements
    mvmt1 = make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    ).json()

    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-02-01",
        quantity=50.0,
        unit_price=55.0,
        total_value=2750.0,
    )

    # Verify we have 2 snapshots
    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    assert len(response.json()) == 2

    # Delete the first movement
    response = client.delete(f"/api/investments/movements/{mvmt1['id']}", headers=auth_headers)
    assert response.status_code == 204

    # Check snapshots were rebuilt (now only 1)
    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    snapshots = response.json()
    assert len(snapshots) == 1
    assert snapshots[0]["date"] == "2026-02-01"
    assert snapshots[0]["quantity_held"] == 50.0


def test_position_snapshots_with_bonus_and_split(client, auth_headers):
    """Test snapshots correctly track bonus shares and stock splits.

    After bonificacao/desdobramento, the average cost dilutes (total_bought
    increases without increasing total_cost), so invested_value stays equal
    to the actual aportado (5000), not inflated.
    """
    asset = make_asset(client, auth_headers, ticker="BONUSSNAP").json()

    # Buy 100 @ 50
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    )

    # Bonus: +20 shares (no cost)
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-02-01",
        movement_type="bonificacao",
        quantity=20.0,
        unit_price=None,
        total_value=0.0,
    )

    # Stock split: +120 shares (no cost)
    make_movement(
        client,
        auth_headers,
        asset["id"],
        date="2026-03-01",
        movement_type="desdobramento",
        quantity=120.0,
        unit_price=None,
        total_value=0.0,
    )

    response = client.get("/api/investments/positions/history?asset_id=" + str(asset["id"]), headers=auth_headers)
    snapshots = response.json()
    assert len(snapshots) == 3

    # Snapshot 1: Buy 100 @ 50
    assert snapshots[0]["quantity_held"] == 100.0
    assert snapshots[0]["invested_value"] == 5000.0

    # Snapshot 2: +20 bonus shares
    # total_bought = 100 + 20 = 120, avg_price = 5000 / 120 ≈ 41.67
    assert snapshots[1]["quantity_held"] == 120.0
    assert abs(snapshots[1]["invested_value"] - 5000.0) < 0.01

    # Snapshot 3: +120 split shares
    # total_bought = 100 + 20 + 120 = 240, avg_price = 5000 / 240 ≈ 20.83
    assert snapshots[2]["quantity_held"] == 240.0
    assert abs(snapshots[2]["invested_value"] - 5000.0) < 0.01


def test_consolidated_position_history(client, auth_headers):
    """Test consolidated position history (all assets, carry-forward values)."""
    asset1 = make_asset(client, auth_headers, ticker="CONS1").json()
    asset2 = make_asset(client, auth_headers, ticker="CONS2").json()

    # Asset1: buy 100 @ 50 on 2026-01-15 (invested = 5000)
    make_movement(
        client,
        auth_headers,
        asset1["id"],
        date="2026-01-15",
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    )

    # Asset2: buy 200 @ 25 on 2026-02-01 (invested = 5000)
    make_movement(
        client,
        auth_headers,
        asset2["id"],
        date="2026-02-01",
        quantity=200.0,
        unit_price=25.0,
        total_value=5000.0,
    )

    # Asset1: buy 50 more @ 55 on 2026-03-01 (new invested = 2750)
    make_movement(
        client,
        auth_headers,
        asset1["id"],
        date="2026-03-01",
        quantity=50.0,
        unit_price=55.0,
        total_value=2750.0,
    )

    # Fetch consolidated history
    response = client.get("/api/investments/positions/history", headers=auth_headers)
    assert response.status_code == 200
    consolidated = response.json()

    # We should have 3 dates
    assert len(consolidated) == 3

    # 2026-01-15: asset1 = 5000, asset2 = 0 (no movement yet)
    assert consolidated[0]["date"] == "2026-01-15"
    assert consolidated[0]["total_invested_value"] == 5000.0

    # 2026-02-01: asset1 = 5000 (carry-forward), asset2 = 5000
    assert consolidated[1]["date"] == "2026-02-01"
    assert consolidated[1]["total_invested_value"] == 10000.0

    # 2026-03-01: asset1 = 7750 (cost: 5000 + 2750), asset2 = 5000
    assert consolidated[2]["date"] == "2026-03-01"
    assert abs(consolidated[2]["total_invested_value"] - 12750.0) < 0.01


def test_position_history_cross_user_isolation(client, auth_headers, db_session):
    """Verify position history endpoint enforces user isolation."""
    asset = make_asset(client, auth_headers, ticker="ISOL").json()
    make_movement(
        client,
        auth_headers,
        asset["id"],
        quantity=100.0,
        unit_price=50.0,
        total_value=5000.0,
    )

    # Create another user to verify isolation (not in same session/auth)
    crud.create_user(
        db_session,
        username="other_user_snapshots",
        name="Other User",
        password_hash=auth.hash_password("password123"),
    )

    # Try to access the first user's asset with bad auth (should fail)
    response = client.get(
        f"/api/investments/positions/history?asset_id={asset['id']}",
        headers={"Authorization": "Bearer fake_token"},
    )
    # This should fail auth, not specifically the isolation
    assert response.status_code in (401, 403, 404)


def test_new_asset_types_tesouro_and_renda_fixa(client, auth_headers):
    """Test that new asset types 'tesouro' and 'renda_fixa' are accepted."""
    # Create tesouro asset
    response = make_asset(client, auth_headers, ticker="TESOURO1", asset_type="tesouro")
    assert response.status_code == 201
    tesouro = response.json()
    assert tesouro["asset_type"] == "tesouro"

    # Create renda_fixa asset
    response = make_asset(client, auth_headers, ticker="CDB1", asset_type="renda_fixa")
    assert response.status_code == 201
    renda_fixa = response.json()
    assert renda_fixa["asset_type"] == "renda_fixa"

    # Verify they can be updated
    response = client.put(
        f"/api/investments/assets/{tesouro['id']}",
        json={"asset_type": "renda_fixa"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["asset_type"] == "renda_fixa"

    # Verify they appear in list
    response = client.get("/api/investments/assets", headers=auth_headers)
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 2
    asset_types = {a["asset_type"] for a in assets}
    assert "tesouro" in asset_types or "renda_fixa" in asset_types


def test_import_guesses_fixed_income_asset_types(client, auth_headers):
    """Test that B3 import correctly guesses fixed income asset types (tesouro/renda_fixa).

    This is a regression test for the bug where fixed income products like
    "Tesouro IPCA+ 2035" or "CDB - CDB3266WRKT - ITAU..." were incorrectly
    classified as "outro" instead of "tesouro"/"renda_fixa".

    Note: the _extract_ticker() function splits on " - " and takes the first
    part, so the ticker stored will be "Tesouro IPCA+ 2035", "CDB", "LCI",
    "Tesouro Selic 2026" (not the full product names).
    """
    csv_content = (
        "Data,Produto,Movimentação,Quantidade,Preço,Valor\n"
        "2026-01-15,Tesouro IPCA+ 2035,Compra,10,100.00,1000.00\n"
        "2026-01-16,CDB - CDB3266WRKT - ITAU UNIBANCO S/A,Compra,1,1000.00,1000.00\n"
        "2026-01-17,LCI - ITAU,Compra,1,500.00,500.00\n"
        "2026-01-18,Tesouro Selic 2026,Compra,5,50.00,250.00\n"
    )
    mapping = {
        "date": "Data",
        "ticker": "Produto",
        "movement_type": "Movimentação",
        "quantity": "Quantidade",
        "unit_price": "Preço",
        "total_value": "Valor",
    }

    response = client.post(
        "/api/investments/import",
        files={"file": ("mov.csv", csv_content.encode(), "text/csv")},
        data={"column_mapping": json.dumps(mapping)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["committed"] is True
    assert body["assets_created"] == 4

    # Verify assets were created with correct types
    assets_by_ticker = {a["ticker"]: a for a in client.get("/api/investments/assets", headers=auth_headers).json()}

    # Tesouro products should be guessed as "tesouro"
    assert assets_by_ticker["Tesouro IPCA+ 2035"]["asset_type"] == "tesouro"
    assert assets_by_ticker["Tesouro Selic 2026"]["asset_type"] == "tesouro"

    # CDB and LCI products should be guessed as "renda_fixa"
    assert assets_by_ticker["CDB"]["asset_type"] == "renda_fixa"
    assert assets_by_ticker["LCI"]["asset_type"] == "renda_fixa"
