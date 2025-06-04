# app.py (Google Sheets version)

import os
import json
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict

# Google Sheets setup
SHEET_ID = "1Su63LEQ_DeR0LUu_RFL44pRFqpeGCo3SfH8Zz3sauhU"  # replace with your real sheet ID
CREDENTIALS_FILE = "grocerease-461918-3d7c959bcbfc.json"  # upload this to your project root

app = Flask(__name__)


def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    creds_dict = json.loads(os.environ['GOOGLE_CREDENTIALS_JSON'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def add_to_sheet(recipe, ingredient, quantity, unit):
    sheet = get_sheet()
    sheet.append_row([recipe, ingredient, quantity, unit])


def get_all_rows():
    sheet = get_sheet()
    return sheet.get_all_records()


def get_recipe_names():
    return sorted(set(row["Recipe"] for row in get_all_rows()))


def get_all_ingredients():
    return sorted(set(row["Ingredient"] for row in get_all_rows() if row["Ingredient"]))


@app.route('/')
def index():
    recipe_names = get_recipe_names()
    all_ingredients = get_all_ingredients()
    return render_template('index.html', recipe_names=recipe_names, all_ingredients=all_ingredients)


@app.route('/submit', methods=['POST'])
def submit():
    recipe = request.form['recipe']
    ingredients = request.form.getlist('ingredient')
    quantities = request.form.getlist('quantity')
    units = request.form.getlist('unit')

    for i in range(len(ingredients)):
        if ingredients[i].strip():
            add_to_sheet(recipe, ingredients[i], quantities[i], units[i])

    return redirect('/')


@app.route('/recipes')
def recipes():
    recipe_names = get_recipe_names()
    return render_template('recipes.html', recipe_names=recipe_names)


@app.route('/recipes/<name>')
def recipe_detail(name):
    rows = get_all_rows()
    ingredients = [(row['Ingredient'], row['Quantity'], row['Unit']) for row in rows if row['Recipe'] == name]
    all_ingredients = get_all_ingredients()
    return render_template('recipe_detail.html', recipe=name, ingredients=ingredients, all_ingredients=all_ingredients)


@app.route('/update/<name>', methods=['POST'])
def update_recipe(name):
    # Since Google Sheets has no direct delete by condition, we reload the sheet
    sheet = get_sheet()
    data = sheet.get_all_values()
    headers = data[0]
    filtered = [row for row in data if row[0] != name or row == headers]

    # Clear and reupload (reset sheet)
    sheet.clear()
    sheet.append_row(headers)
    for row in filtered[1:]:
        sheet.append_row(row)

    # Add new rows
    ingredients = request.form.getlist('ingredient')
    quantities = request.form.getlist('quantity')
    units = request.form.getlist('unit')

    for i in range(len(ingredients)):
        if ingredients[i].strip():
            sheet.append_row([name, ingredients[i], quantities[i], units[i]])

    return redirect(url_for('recipe_detail', name=name))


@app.route('/shopping', methods=['GET', 'POST'])
def shopping_list():
    recipe_names = get_recipe_names()
    ingredients_summary = []

    if request.method == 'POST':
        selected_recipes = request.form.getlist('recipes')
        rows = get_all_rows()
        selected = [r for r in rows if r['Recipe'] in selected_recipes]

        conversion_table = {
            ('kg', 'g'): 1000, ('g', 'g'): 1, ('gousses', 'gousses'): 1,
            ('c. à s.', 'mL'): 15, ('c. à c.', 'mL'): 5,
            ('mL', 'mL'): 1, ('L', 'mL'): 1000, ('pincée', 'pincée'): 1,
            ('bouquet', 'bouquet'): 1, ('poignée', 'poignée'): 1, ('-', '-'): 1,
        }

        aggregated = defaultdict(lambda: defaultdict(float))

        for row in selected:
            ing, qty, unit = row['Ingredient'], row['Quantity'], row['Unit']
            qty = float(qty or 0)
            ing_key = (ing.strip().lower(), unit)
            if unit in ['kg', 'g']:
                target = 'g'
            elif unit in ['L', 'c. à s.', 'c. à c.', 'mL']:
                target = 'mL'
            else:
                target = unit
            conv = conversion_table.get((unit, target), None)
            if conv:
                aggregated[(ing, target)][unit] += qty * conv
            else:
                aggregated[(ing, unit)][unit] += qty

        ingredients_summary = [
            {'ingredient': ing, 'quantity': round(sum(units.values())), 'unit': unit}
            for (ing, unit), units in aggregated.items()
        ]

    return render_template('shopping.html', recipes=recipe_names, ingredients=ingredients_summary)


if __name__ == '__main__':
    app.run(debug=True)
