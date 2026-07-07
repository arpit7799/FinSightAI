from pydantic import BaseModel


class RiskPredictionRequest(BaseModel):

    Year: int
    Industry_Type: str
    Firm_Size: str

    Total_Assets: float
    Total_Liabilities: float
    Total_Revenue: float
    Net_Income: float

    Current_Assets: float
    Current_Liabilities: float

    Cash_Flow: float

    Debt_to_Equity_Ratio: float

    Current_Ratio: float
    Quick_Ratio: float

    Return_on_Assets: float
    Return_on_Equity: float

    Gross_Profit_Margin: float
    Operating_Margin: float

    Asset_Turnover_Ratio: float

    Interest_Coverage_Ratio: float

    Working_Capital: float

    Revenue_Growth_Rate: float
    Net_Profit_Growth_Rate: float

    Cash_Flow_Ratio: float