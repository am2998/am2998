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
    # Add days from previous month
    last_month = today.replace(day=1) - timedelta(days=1)
    days += last_month.day

if months < 0:
    # Borrow from years
    years -= 1
    months += 12

# Update the uptime in README
new_uptime = f"Uptime: {years}y {months}m {days}d"
new_readme = re.sub(uptime_pattern, new_uptime, new_readme)

# Update the last updated date tag
last_update_pattern = r"<!-- LAST_UPDATED: (\d{4}-\d{2}-\d{2}) -->"
new_last_update = f"<!-- LAST_UPDATED: {today.strftime('%Y-%m-%d')} -->"

if re.search(last_update_pattern, new_readme):
    new_readme = re.sub(last_update_pattern, new_last_update, new_readme)
else:
    # Add the tag if it doesn't exist (right after commits section)
    new_readme = new_readme.replace(end_tag, end_tag + f"\n{new_last_update}")

with open("README.md", "w") as f:
    f.write(new_readme)
