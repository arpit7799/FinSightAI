class RatioCalculationService:

    @staticmethod
    def safe_divide(a, b):
        if a is None or b in (None, 0):
            return None

        return round(a / b, 4)

    @classmethod
    def calculate(cls, data):

        ratios = {}

        revenue = data.revenue
        net_income = data.net_income
        operating_income = data.operating_income

        assets = data.total_assets
        liabilities = data.total_liabilities
        equity = data.total_equity

        cash = data.cash
        inventory = data.inventory
        receivables = data.receivables
        debt = data.debt

        eps = data.eps
        shares = data.shares_outstanding

        # Liquidity

        current_assets = None
        current_liabilities = None

        if cash is not None or inventory is not None or receivables is not None:
            current_assets = sum(
                value
                for value in [cash, inventory, receivables]
                if value is not None
            )

        if liabilities is not None:
            current_liabilities = liabilities

        ratios["current_ratio"] = cls.safe_divide(
            current_assets,
            current_liabilities,
        )

        ratios["quick_ratio"] = cls.safe_divide(
            None if current_assets is None or inventory is None else current_assets - inventory,
            current_liabilities,
        )

        ratios["cash_ratio"] = cls.safe_divide(
            cash,
            current_liabilities,
        )

        # Profitability

        ratios["roa"] = cls.safe_divide(
            net_income,
            assets,
        )

        ratios["roe"] = cls.safe_divide(
            net_income,
            equity,
        )

        ratios["gross_margin"] = None

        ratios["operating_margin"] = cls.safe_divide(
            operating_income,
            revenue,
        )

        ratios["net_margin"] = cls.safe_divide(
            net_income,
            revenue,
        )

        # Efficiency

        ratios["asset_turnover"] = cls.safe_divide(
            revenue,
            assets,
        )

        ratios["inventory_turnover"] = None

        ratios["receivables_turnover"] = cls.safe_divide(
            revenue,
            receivables,
        )

        # Leverage

        ratios["debt_to_equity"] = cls.safe_divide(
            debt,
            equity,
        )

        ratios["debt_to_assets"] = cls.safe_divide(
            debt,
            assets,
        )

        ratios["interest_coverage"] = None

        # Market

        ratios["eps"] = eps

        ratios["book_value_per_share"] = cls.safe_divide(
            equity,
            shares,
        )

        ratios["pe_ratio"] = None

        ratios["price_to_book"] = None

        ratios["dividend_yield"] = None

        # Health Score

        score = 100

        if ratios["current_ratio"] is not None and ratios["current_ratio"] < 1:
            score -= 15

        if ratios["debt_to_equity"] is not None and ratios["debt_to_equity"] > 2:
            score -= 20

        if ratios["roa"] is not None and ratios["roa"] < 0.05:
            score -= 15

        if ratios["roe"] is not None and ratios["roe"] < 0.10:
            score -= 15

        if ratios["net_margin"] is not None and ratios["net_margin"] < 0.05:
            score -= 15

        ratios["health_score"] = max(score, 0)

        return ratios