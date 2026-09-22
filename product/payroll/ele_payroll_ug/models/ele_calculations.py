from decimal import Decimal, InvalidOperation

def _decimal(value, label):
    """Convert a payroll value to a safe non-negative decimal"""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f'{label} must be a valid number') from error

    if not amount.is_finite() or amount < 0:
        raise ValueError(f'{label} must be a finite and non-negative')

    return amount

def resident_paye(
    chargeable_income,
    bands,
    surcharge_threshold,
    surcharge_rate,
):
    """Calculate monthly PAYE for a resident employee
    Each band is a tuple containing lower limit, upper limit, and tax rate.

    The upper limit may be None for the final open-ended band.
    """
    income = _decimal(chargeable_income, 'Chargeable Income')
    surcharge_threshold = _decimal(surcharge_threshold, 'Surcharge Threshold')
    surcharge_rate = _decimal(surcharge_rate, 'Surcharge Rate')
    tax = Decimal('0')

    # Apply each tax rate only to the part of the income inside that band.
    for lower, upper, rate in bands:
        lower = _decimal(lower, 'PAYE band lower limit')
        upper = (
            _decimal(upper, 'PAYE band upper limit')
            if upper is not None
            else None
        )
        rate = _decimal(rate, 'PAYE band rate')

        if upper is not None and upper <= lower:
            raise ValueError('PAYE band upper limit must exceed its lower limit')

        # Income below this band's lower limit is not taxed in this band
        taxable_amount = income - lower

        if taxable_amount <= 0:
            continue

        # A closed band must not tax income above its upper limit.
        if upper is not None:
            taxable_amount = min(taxable_amount, upper - lower)

        tax += taxable_amount * rate

    # Income above the statutory threshold receives an additional surcharge
    if income > surcharge_threshold:
        tax += (income - surcharge_threshold) * surcharge_rate

    return tax

def lst_installment(
    cash_gross,
    taxable_income,
    month,
    lst_bands,
    collection_months,
    installment_count,
    paye_bands,
    surcharge_threshold,
    surcharge_rate
):
    """Calculate the employee's monthly local service tax installment.

    LST is assessed annually from monthly take-home salary and collected in
    equal installments during the configured collection months. Because LST reduces
    PAYE chargeable income while lst band depends on salary after PAYE, each possible
    LST band is tested until a stable result is found."""

    cash_gross = _decimal(cash_gross, "Cash Gross")
    taxable_income = _decimal(taxable_income, "Taxable Income")

    if not isinstance(month, int) or not 1 <= month <= 12:
        raise ValueError("Month must be an integer from 1 to 12")

    collection_months = tuple(int(value) for value in collection_months)

    if any(value < 1 or value > 12 for value in collection_months):
        raise ValueError("LST collection months must also be between 1 and 12")

    installment_count = _decimal(installment_count, "LST Installment Count")

    if installment_count == 0:
        raise ValueError("LST Installment count must be greater than zero")

    if month not in collection_months:
        return Decimal("0")

    valid_installments = []

    for index, (lower, upper, annual_lst) in enumerate(lst_bands):
        lower = _decimal(lower, "LST Band lower limit")
        upper = (
            _decimal(upper, "LST band upper limit")
            if upper is not None
            else None
        )
        annual_lst = _decimal(annual_lst, "Annual LST")

        if upper is not None and upper <= lower:
            raise ValueError("LST band upper limit must exceed its lower limit")

        installment = annual_lst / installment_count

        chargeable_income = max(
            Decimal("0"),
            taxable_income - installment
        )

        paye = resident_paye(
            chargeable_income=chargeable_income,
            bands=paye_bands,
            surcharge_threshold=surcharge_threshold,
            surcharge_rate=surcharge_rate,
        )

        # The legislation describes the assessment basis as gross salary after PAYE.
        # Employee NSSF is not deducted when selecting the band
        take_home_salary = max(
            Decimal("0"),
            cash_gross - paye
        )

        # Statutory wording uses exceeding for each positive lower limit
        above_lower = (
            take_home_salary >= lower
            if index == 0
            else take_home_salary > lower
        )

        below_upper = (
            upper is None
            or take_home_salary <= upper
        )

        if above_lower and below_upper:
            valid_installments.append(installment)

    if len(valid_installments) != 1:
        raise ValueError("LST Bands did not produce one stable PAYE/LST result")

    return valid_installments[0]

def nssf_contribution(wage_base, rate):
    """Calculate an NSSF contribution from the applicable cash wage base."""
    wage_base = _decimal(wage_base, 'NSSF wage base')
    rate = _decimal(rate, 'NSSF rate')
    return wage_base * rate