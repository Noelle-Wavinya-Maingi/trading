# -*- coding: utf-8 -*-
"""Convert trading.trade.ele_win_rate from float to boolean.

ele_win_rate started out as a stored float percentage and was redefined as a
Boolean (win/loss) without a migration. Odoo's own upgrade machinery does not
convert existing column data to a new type, so on any database that installed
the old float version this leaves the ALTER TABLE either failing outright or
succeeding with unreadable values. Existing float data is treated as "win" for
any strictly positive value, matching the field's own compute
(record.ele_win_rate = record.ele_realized_pnl > 0).
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute("""
        SELECT udt_name FROM information_schema.columns
         WHERE table_name = 'trading_trade' AND column_name = 'ele_win_rate'
    """)
    row = cr.fetchone()
    if not row or row[0] == 'bool':
        return

    cr.execute("""
        ALTER TABLE trading_trade
        ALTER COLUMN ele_win_rate TYPE bool USING (ele_win_rate > 0)
    """)
