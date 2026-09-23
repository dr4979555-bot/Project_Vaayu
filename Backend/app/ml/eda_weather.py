import pandas as pd
import matplotlib.pyplot as plt


DATA_PATH = "data/patna_weather_2021_2025.csv"


def main():
    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)
    df["time"] = pd.to_datetime(df["time"])

    # Time features
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month
    df["hour"] = df["time"].dt.hour

    # --------------------------------------------------
    # 1. Average temperature by month
    # --------------------------------------------------
    monthly_temp = df.groupby("month")["temperature_2m"].mean()

    plt.figure(figsize=(10, 5))
    plt.plot(monthly_temp.index, monthly_temp.values, marker="o")
    plt.title("Average Temperature by Month - Patna")
    plt.xlabel("Month")
    plt.ylabel("Temperature (°C)")
    plt.xticks(range(1, 13))
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------
    # 2. Average temperature by hour
    # --------------------------------------------------
    hourly_temp = df.groupby("hour")["temperature_2m"].mean()

    plt.figure(figsize=(10, 5))
    plt.plot(hourly_temp.index, hourly_temp.values, marker="o")
    plt.title("Average Temperature by Hour")
    plt.xlabel("Hour of Day")
    plt.ylabel("Temperature (°C)")
    plt.xticks(range(0, 24))
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------
    # 3. Temperature distribution
    # --------------------------------------------------
    plt.figure(figsize=(10, 5))
    plt.hist(df["temperature_2m"], bins=40)
    plt.title("Temperature Distribution")
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------
    # 4. Rainfall distribution
    # --------------------------------------------------
    rainfall = df[df["precipitation"] > 0]["precipitation"]

    plt.figure(figsize=(10, 5))
    plt.hist(rainfall, bins=40)
    plt.title("Hourly Rainfall Distribution")
    plt.xlabel("Precipitation (mm)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------
    # 5. Correlation matrix
    # --------------------------------------------------
    numeric_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "weather_code",
    ]

    correlation = df[numeric_columns].corr()

    print("\n========== CORRELATION WITH TEMPERATURE ==========")
    print(
        correlation["temperature_2m"]
        .sort_values(ascending=False)
        .round(3)
    )

    # --------------------------------------------------
    # 6. Basic seasonal statistics
    # --------------------------------------------------
    print("\n========== MONTHLY TEMPERATURE ==========")
    print(monthly_temp.round(2))

    print("\n========== HOURLY TEMPERATURE ==========")
    print(hourly_temp.round(2))


if __name__ == "__main__":
    main()