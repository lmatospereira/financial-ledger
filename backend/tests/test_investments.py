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
    """Test portfolio with bonus shares and stock split."""
    asset = make_asset(client, auth_headers, ticker="BONUS").json()

    # Buy 100 @ 50.00 = 5000.00
    make_movement(client, auth_headers, asset["id"], quantity=100.0, unit_price=50.0, total_value=5000.0)

    # Bonus: +20 shares (no cost)
    make_movement(
        client,
        auth_headers,
        asset["id"],
        movement_type="bonificacao",
        quantity=20.0,
        unit_price=None,
        total_value=0.0,
    )

    # Stock split 2:1: we now have 240 (doubled)
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
    assert position["avg_price"] == 50.0  # Still based only on "compra"
    assert position["total_invested"] == 12000.0


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
