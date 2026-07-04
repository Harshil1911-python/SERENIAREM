# SERENIA - Debit Credit
A web based double entry accounting software to do tasks from double entry to generate financial statements in Excel format.
#### Video Demo:
[![Video Demo](https://img.youtube.com/vi/VyvKvPro5_g/0.jpg)](https://www.youtube.com/watch?v=VyvKvPro5_g)

## Website link
I have deployed it to pythonanywhere.com and [here](https://Serenia.pythonanywhere.com/) is the link.

## Requirements
Install the required packages with the following command.

```
pip install -r requirements.txt
```

The openpyxl library is used in order to deal with Excel files when generating the statements.

[Google Fonts](https://fonts.google.com/) is used for the font of this website.

[Bootsrap](https://getbootstrap.com/) is used in this application to make the webstie to have a nicer look.

## Usage

Run following command to initialise database and create tables.

```
python createdb.py
```

After that, run following following comand to run flask app and head over to port 5000 in browser (by default).

```
python index.py
```

## Database
Sqlite3 is used in this application due to its simpleness.

There are 3 tables in this database which are:
- persons
- accounts
- transactions

## About the project
### Home page (not signed in)
- Home page for users that has not signed in

Users will be redirected to this page if they have not signed in.

### Log in page
- Page for users to log in

The username and password must be matched to the database before the user logs in. Session in flask library is used to remember the user.

### Sign up page
- Page for users to sign up

Username, password, confirmation password and currency is needed or else an error message will be displayed. Users have to agree to the terms of use before signing up. Users will be directed to the home page of the user after signing up.

### Home page (signed in)
- Home page for users that has already signed in

Cash and cash equivalents balances and profit is being displayed in the page by using SQL query. All input fields must be filled in or else the website will alert the user by using Javasript. The users can also enter their double entry of their transaction and hand it to the database. There is also a data table in the page to show recent transactions by using [DataTable](https://datatables.net/examples/styling/bootstrap4).

### Add an account
- Add a new account according to their type and subtype

The subtype will be changed once the user change the type in the select option by using Javascript. The account wil be added into the database once the user clicks the save button.

### View accounts
- View all the accounts and their details

Users can access each individual account by clicking the link based on their id in the accounts table in database. 

### View individual account
- View details of individual account and let users to delete account.

Users will be directed to the home page if the id is not in the database or the account is not belongs to the user.

Users will be asked to confirm before deleting the account.

### Statements
- View financial statements of Trial Balance, Statement of Profit or Loss (SOPL) and Statement of Financial Position (SOFP) in a table.

The user can only choose year in SOPL because the other two statements are balances at a point of time but SOPL shows the profit or loss for a period of time.

### Download as Excel
- Download financial statements in Excel format.

Using openpyxl library to insert value into the workbook and bold some of the cells which is same to the table displayed in the individual statement page.

### Profile
- View details of the user and let the user to change password

### Log out
The user will be logged out after clicking the log out button and the user session will be cleared.

## Acknowledgement
A final project of [CS50x](https://cs50.harvard.edu/x/2026/). A big thanks to the team of CS50x for the wonderful course.
