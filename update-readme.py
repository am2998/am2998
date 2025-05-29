import re
from datetime import datetime, timedelta

# Update uptime
uptime_pattern = r"Uptime: (\d+)y (\d+)m (\d+)d"
# Calculate uptime based on time since September 29, 1998
birth_date = datetime(1998, 9, 29).date()
# Get current date
today = datetime.now().date()

# Calculate years, months, and days since birth date
years = today.year - birth_date.year
months = today.month - birth_date.month
days = today.day - birth_date.day

# Adjust for negative months or days
if days < 0:
    # Borrow from months
    months -= 1
    # Calculate days in the previous month
    if today.month == 1:  # January
        last_month_days = 31  # December has 31 days
    else:
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_days = last_month.day
    days += last_month_days

if months < 0:
    # Borrow from years
    years -= 1
    months += 12

# Read the README file
with open("README.md", "r") as f:
    new_readme = f.read()

# Update the uptime in README
new_uptime = f"Uptime: {years}y {months}m {days}d"
new_readme = re.sub(uptime_pattern, new_uptime, new_readme)

with open("README.md", "w") as f:
    f.write(new_readme)
