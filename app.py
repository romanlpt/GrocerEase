import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# SQLite Database setup
def init_db():
    conn = sqlite3.connect('recipes.db')  # 'recipes.db' is the database file
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe TEXT NOT NULL,
            ingredient TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Function to insert recipe data
def add_to_db(recipe, ingredient, quantity, unit):
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recipes (recipe, ingredient, quantity, unit)
        VALUES (?, ?, ?, ?)
    ''', (recipe, ingredient, quantity, unit))
    conn.commit()
    conn.close()


# Function to retrieve recipes from the database
def get_recipes():
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute('SELECT recipe, ingredient, quantity, unit FROM recipes')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_recipe_names():
    # Query only distinct recipe names from the database
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT recipe FROM recipes")
    names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return names
def get_all_ingredients():
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ingredient FROM recipes")  # or ingredients table if named differently
    ingredients = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ingredients

@app.route('/')
def index():
    recipe_names = get_recipe_names()
    all_ingredients = get_all_ingredients()
    return render_template('index.html', recipe_names=recipe_names, all_ingredients=all_ingredients)



@app.route('/add', methods=['POST'])
def add_recipe():
    recipe = request.form['recipe']
    ingredient = request.form['ingredient']
    quantity = request.form['quantity']
    unit = request.form['unit']
    
    add_to_db(recipe, ingredient, quantity, unit)

    # Redirect and keep the recipe name in the URL
    return redirect(url_for('index', recipe=recipe))

@app.route('/submit', methods=['POST'])
def submit():
    recipe = request.form['recipe']

    # Extract multiple rows of ingredient data
    ingredients = request.form.getlist('ingredient')
    quantities = request.form.getlist('quantity')
    units = request.form.getlist('unit')

    for i in range(len(ingredients)):
        if ingredients[i].strip():  # Skip empty rows
            add_to_db(recipe, ingredients[i], quantities[i], units[i])

    return redirect('/')

@app.route('/recipes')
def recipes():
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT recipe FROM recipes")
    recipe_names = [row[0] for row in cursor.fetchall()]
    conn.close()
    return render_template('recipes.html', recipe_names=recipe_names)

@app.route('/recipes/<name>')
def recipe_detail(name):
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ingredient, quantity, unit FROM recipes WHERE recipe = ?', (name,))
    ingredients = cursor.fetchall()

    cursor.execute('SELECT DISTINCT ingredient FROM recipes')
    all_ingredients = [row[0] for row in cursor.fetchall()]

    conn.close()
    return render_template('recipe_detail.html', recipe=name, ingredients=ingredients, all_ingredients=all_ingredients)


@app.route('/update/<name>', methods=['POST'])
def update_recipe(name):
    # Clear old entries
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM recipes WHERE recipe = ?', (name,))
    conn.commit()

    # Insert new ones
    ingredients = request.form.getlist('ingredient')
    quantities = request.form.getlist('quantity')
    units = request.form.getlist('unit')

    for i in range(len(ingredients)):
        if ingredients[i].strip():  # Skip empty lines
            cursor.execute('''
                INSERT INTO recipes (recipe, ingredient, quantity, unit)
                VALUES (?, ?, ?, ?)
            ''', (name, ingredients[i], quantities[i], units[i]))

    conn.commit()
    conn.close()

    return redirect(url_for('recipe_detail', name=name))


from collections import defaultdict

# Table de conversion
conversion_table = {
    ('kg', 'g'): 1000,
    ('g', 'g'): 1,
    ('gousses', 'gousses'): 1,
    ('c. à s.', 'mL'): 15,
    ('c. à c.', 'mL'): 5,
    ('mL', 'mL'): 1,
    ('L', 'mL'): 1000,
    ('pincée', 'pincée'): 1,
    ('bouquet', 'bouquet'): 1,
    ('poignée', 'poignée'): 1,
    ('-', '-'): 1,
}

@app.route('/shopping', methods=['GET', 'POST'])
def shopping_list():
    conn = sqlite3.connect('recipes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT recipe FROM recipes")
    recipe_names = [row[0] for row in cursor.fetchall()]

    ingredients_summary = []

    if request.method == 'POST':
        selected_recipes = request.form.getlist('recipes')
        cursor.execute('SELECT ingredient, quantity, unit FROM recipes WHERE recipe IN ({seq})'
                       .format(seq=','.join(['?']*len(selected_recipes))), selected_recipes)
        ingredients = cursor.fetchall()
        conn.close()

        aggregated = defaultdict(lambda: defaultdict(float))

        for ing, qty, unit in ingredients:
            # Try to normalize to g or mL when possible
            key = (ing.strip().lower(), unit)
            if unit in ['kg', 'g']:
                target = 'g'
            elif unit in ['L', 'c. à s.', 'c. à c.', 'mL']:
                target = 'mL'
            else:
                target = unit

            conversion = conversion_table.get((unit, target), None)
            if conversion:
                aggregated[(ing, target)][unit] += float(qty) * conversion
            else:
                aggregated[(ing, unit)][unit] += float(qty)

        ingredients_summary = [
            {'ingredient': ing, 'quantity': round(sum(units.values())), 'unit': unit}
            for (ing, unit), units in aggregated.items()
        ]

    else:
        conn.close()

    return render_template('shopping.html', recipes=recipe_names, ingredients=ingredients_summary)


if __name__ == '__main__':
    init_db()  # Initialize the database on app start
    app.run(debug=True)
