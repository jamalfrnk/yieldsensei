import asyncio
import json
from services.technical_analysis import calculate_support_resistance, get_signal_analysis

async def test_support_resistance():
    # Load sample price data from CoinGecko API response
    with open('test_data.json', 'w') as f:
        sample_data = {
            "prices": [
                [1739750400000, 96149.34],
                [1739664000000, 97569.95],
                [1739577600000, 97488.48],
                [1739491200000, 96561.66],
                [1739404800000, 97836.18],
                [1739318400000, 95739.97],
                [1739232000000, 97399.98],
                [1739145600000, 96548.57],
                [1739059200000, 96558.23],
                [1738972800000, 96558.45],
            ]
        }
        json.dump(sample_data, f)

    # Extract prices for testing
    prices = [price[1] for price in sample_data["prices"]]
    
    # Test support/resistance calculation
    levels = calculate_support_resistance(prices)
    
    # Verify formatting and spacing
    print("\nSupport/Resistance Test Results:")
    print(f"Support 2: {levels['support_2']}")
    print(f"Support 1: {levels['support_1']}")
    print(f"Current Price: ${prices[-1]:,.2f}")
    print(f"Resistance 1: {levels['resistance_1']}")
    print(f"Resistance 2: {levels['resistance_2']}")
    
    # Test full signal analysis
    signal_data = await get_signal_analysis("bitcoin")
    print("\nSignal Analysis Test Results:")
    for key, value in signal_data.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(test_support_resistance())
