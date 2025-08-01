.PHONY: watch run

# The main script you want to rerun
SCRIPT=src/manager/main.py

# Watch for changes and rerun the script
watch:
	poetry run watchmedo shell-command \
		--patterns="*.py" \
		--recursive \
		--command='clear && poetry run python $(SCRIPT) roan' .

# Run once
run:
	poetry run python $(SCRIPT) roan
