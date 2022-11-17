import argparse
import sqlite3
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def create_connection(db_path: str) -> sqlite3.Connection | None:
    """ Create a database connection to the SQLite database
    :param db_path: path to a database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(e)

    return conn


def create_table(conn: sqlite3.Connection, create_table_sql: str):
    """ Create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)


def insert_product(conn: sqlite3.Connection, product: tuple) -> int | None:
    """
    Insert a new product into the products table
    :param conn: Connection object
    :param product: Product to insert 
    :return: Product id or None
    """
    sql = ''' INSERT OR IGNORE INTO products (id, name, detail, price, top_review)
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, product)
    conn.commit()
    return cur.lastrowid


def main():
    # parse arguments
    parser = argparse.ArgumentParser(description='Scrape some products.')
    parser.add_argument('--stars', metavar='N', default=3, type=int, help='minimum number of stars')
    args = parser.parse_args()

    # make a db connection
    DB_NAME = 'scraped.db'
    CREATE_TABLE_STATEMENT = ''' CREATE TABLE IF NOT EXISTS products (
                                    id integer PRIMARY KEY,
                                    name text,
                                    detail text,
                                    price integer,
                                    top_review integer
                                ); '''

    conn = create_connection(DB_NAME)
    if conn is not None:
        create_table(conn, CREATE_TABLE_STATEMENT)
    else:
        sys.exit("Database connection failed")

    # do your scraping
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(options=chrome_options)

    products = {}
    BASE_URL = 'https://webscraper.io/test-sites/e-commerce/static'

    driver.get(f'{BASE_URL}/computers/laptops')
    while (True):
        try:
            thumbnails = driver.find_elements(By.CLASS_NAME, 'thumbnail')
            for thumbnail in thumbnails:
                rating = int(thumbnail.find_element(By.XPATH, './div/p[@data-rating]').get_attribute('data-rating'))
                # print(rating)
                if rating >= args.stars:
                    anchor = thumbnail.find_element(By.XPATH, './div/h4/a')
                    link = anchor.get_attribute('href')
                    name = anchor.get_attribute('title')
                    id = link[link.rfind('/')+1:]
                    products[id] = {'name': name}
                    # print(link)
                    # print(name)
                    # print(id)
            driver.find_element(By.LINK_TEXT, '›').click()
        except:
            break

    for product, contents in products.items():
        driver.get(f"{BASE_URL}/product/{product}")
        try:
            details = driver.find_element(By.CLASS_NAME, 'description').get_attribute('innerHTML')
            price = driver.find_element(By.CLASS_NAME, 'price').get_attribute('innerHTML')
            ratings = driver.find_element(By.XPATH, "//div[contains(@class, 'ratings')]/p").get_attribute('innerHTML').strip().split(" ")[0]
            contents['details'] = details
            contents['price'] = int(float(price.strip("$"))*100)  # in cents
            contents['top_review'] = int(ratings) >= 10
            insert_product(conn=conn, product=(product, contents["name"], contents["details"], contents["price"], contents["top_review"]))
        except Exception as e:
            print(e)

    driver.quit()


if __name__ == '__main__':
    main()