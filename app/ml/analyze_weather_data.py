import pandas as pd


DATA_PATH = "data/patna_weather_2021_2025.csv"


def main():
    print("Loading weather dataset...\n")

    df = pd.read_csv(DATA_PATH)

    # Convert time column to datetime
    df["time"] = pd.to_datetime(df["time"])

    print("========== DATASET INFO ==========")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\n========== DATE RANGE ==========")
    print(f"Start: {df['time'].min()}")
    print(f"End:   {df['time'].max()}")

    print("\n========== MISSING VALUES ==========")
    print(df.isna().sum())

    print("\n========== DUPLICATES ==========")
    print(df.duplicated().sum())

    print("\n========== STATISTICAL SUMMARY ==========")
    print(df.describe().round(2))

    print("\n========== TEMPERATURE ==========")
    print(f"Minimum: {df['temperature_2m'].min():.2f} °C")
    print(f"Maximum: {df['temperature_2m'].max():.2f} °C")
    print(f"Mean:    {df['temperature_2m'].mean():.2f} °C")

    print("\n========== RAINFALL ==========")
    print(f"Maximum hourly precipitation: {df['precipitation'].max():.2f} mm")
    print(f"Total precipitation: {df['precipitation'].sum():.2f} mm")
    print(f"Hours with rain: {(df['rain'] > 0).sum():,}")

    print("\n========== WEATHER CODES ==========")
    print(df["weather_code"].value_counts().sort_index())

    print("\n========== DATA TYPES ==========")
    print(df.dtypes)


if __name__ == "__main__":
    main()