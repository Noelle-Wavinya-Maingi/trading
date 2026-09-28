# Commodity module demo

Open: <http://localhost:8070>

- Login: `admin`
- Password: `demo`
- Database: `trading_demo`

## Seven minute flow

1. **Full trade:** open `DEMO-FULL-CASHEW`. It already contains the purchase, partial sale, physical lot, remaining stock, additional costs, additional revenue, multicurrency conversion, and complete P&L split. Open its **Budget** to show the planned and actual amounts behind those totals.
2. **Trading board:** briefly show the open coffee trade and the closed shea trade. Explain that one record keeps the commercial and operational picture together.
3. **Purchase:** open Purchase and select `P00001` (`DEMO-COCOA-BUY`). Confirm the order. The module creates and links a 100 unit cocoa trade at EUR 10 per unit.
4. **Trade:** return to Trading. Open the new cocoa trade and point out purchase quantity, purchase price, status, target margin, market price, and P&L fields.
5. **Market move:** enter a current market price of USD 12.00 and a target margin of `20%`. Save. Show the recalculated target price and unrealized position in KES.
6. **Partial sale:** open Sales and select `S00001` (`DEMO-COCOA-SELL`). In Related Trade, choose the new cocoa trade, then confirm the order. This sells 40 of the 100 units at USD 14.
7. **Result and reporting:** return to the cocoa trade, show the linked documents and P&L split, then finish in Trading > Reporting.

## Multicurrency story

- Purchase currency: **EUR**
- Sale and market price currency: **USD**
- Company reporting currency: **KES**
- Demo rates: **EUR 1 = KES 145** and **USD 1 = KES 130**

Use this to explain that the commercial documents retain their original currencies while the trade converts them into KES for one comparable P&L view.

## Restart later

From this repository, run:

```bash
./.demo/start_demo.sh
```

The existing server on port 8069 is separate. This demo uses port 8070 and its own database, so it does not alter the working `trading` database.
