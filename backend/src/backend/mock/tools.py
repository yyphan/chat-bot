from langchain_core.tools import tool

@tool
def mock_get_application_status() -> str:
    """
    Returns the current status of the user's card application.
    """
    return "Your atomic card application status is pending."

@tool
def mock_get_transaction_status(transaction_id: str) -> str:
    """
    Args:
        transaction_id (str): 交易的唯一标识符（交易流水号）。
    """
    if not transaction_id or len(transaction_id) < 4:
        return "Invalid transaction ID, please provide the correct transaction流水号。"
    
    return f"The status of transaction ID {transaction_id} is: [Due to insufficient balance, the payment failed]. Please recharge and try again."