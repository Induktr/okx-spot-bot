import asyncio
import argparse
import os
from dotenv import load_dotenv
from mexc_client import MEXCClient

def validate_symbol(symbol: str):
    """Validate trading symbol format."""
    if not symbol:
        return False, "Symbol is required"

    if '/' not in symbol:
        return False, "Trading pair not found. Please use the BASE/QUOTE format."

    return True, None


def validate_amount(amount: str):
    """Validate amount is positive number."""
    if amount is None:
        return False, "Amount is required"

    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return False, "The quantity must be a positive number."
        return True, None
    except (ValueError, TypeError):
        return False, "The quantity must be a number."


def validate_environment():
    """Check if required environment variables are set."""
    load_dotenv()
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_SECRET_KEY')

    if not api_key or not api_secret:
        print("Error: MEXC_API_KEY and MEXC_SECRET_KEY not found in .env file")
        return False

    return True


async def main():
    if not validate_environment():
        return

    parser = argparse.ArgumentParser(description="MEXC Trading Bot")
    parser.add_argument('--action', required=True, choices=['long', 'short', 'close'], help="Action to perform")
    parser.add_argument('--symbol', help="Trading symbol, e.g., BTC/USDT")
    parser.add_argument('--amount', help="Amount to trade")

    args = parser.parse_args()

    try:
        client = MEXCClient()
    except ValueError as e:
        print(f"Initialization error: {str(e)}")
        return
    if args.action in ['long', 'short']:
        if not args.symbol or not args.amount:
            print("The --symbol and --amount arguments are required for trading.")
            return

        is_valid, error = validate_symbol(args.symbol)
        if not is_valid:
            print(error)
            return

        is_valid, error = validate_amount(args.amount)
        if not is_valid:
            print(error)
            return

        amount_float = float(args.amount)

        await client.prepare()
        if args.action == 'long':
            await client.open_long(args.symbol, amount_float)
        else:
            await client.open_short(args.symbol, amount_float)

    if args.action == 'close':
        if not args.symbol:
             print("Error: --symbol is required for close")
             return
        await client.prepare()
        await client.close_position(args.symbol)
    await client.exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
