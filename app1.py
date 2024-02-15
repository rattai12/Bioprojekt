from flask import Flask, request, render_template
import mysql.connector
from mysql.connector import pooling

app = Flask(__name__)

dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "Rotmos3718!",
    "database": "test2"
}

cnx_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig)

@app.route('/')
def index():
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()

    # Fetch screenings along with movie titles
    cursor.execute("""
        SELECT Screenings.ScreeningID, Movies.Title, Screenings.Timeslot
        FROM Screenings
        JOIN Movies ON Screenings.MovieID = Movies.MovieID
        ORDER BY Movies.Title, Screenings.Timeslot
    """)
    screenings = [{
        'ScreeningID': row[0],
        'Title': row[1],
        'Timeslot': row[2].strftime('%Y-%m-%d %H:%M')  # Formatting for readability
    } for row in cursor.fetchall()]

    # Fetch available seats
    cursor.execute("SELECT SeatID, SeatNb FROM Seats WHERE Status = 'Available'")
    available_seats = [{'SeatID': row[0], 'SeatNb': row[1]} for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template('index1.html', screenings=screenings, available_seats=available_seats)

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    email = request.form['email']
    phone_nb = request.form['phoneNb']
    screening_id = request.form['screening_id']  # This will be passed from the form
    seat_ids = request.form.getlist('seat_ids')  # A list of seat numbers (SeatNb)

    connection = cnx_pool.get_connection()
    cursor = connection.cursor()

    try:
        connection.start_transaction()
        
        cursor.execute("SELECT CustomerID FROM Customers WHERE PhoneNb = %s", (phone_nb,))
        result = cursor.fetchone()
        if result:
            customer_id = result[0]
        else:
            cursor.execute("INSERT INTO Customers (Name, Email, PhoneNb) VALUES (%s, %s, %s)",
                           (name, email, phone_nb))
            customer_id = cursor.lastrowid

        # Insert into Bookings with ScreeningID
        cursor.execute("INSERT INTO Bookings (CustomerID, ScreeningID) VALUES (%s, %s)",
                       (customer_id, screening_id))
        booking_id = cursor.lastrowid

        # Check each seat and insert into BookingSeats
        for seat_nb in seat_ids:
            cursor.execute("SELECT SeatID FROM Seats WHERE SeatNb = %s", (seat_nb,))
            result = cursor.fetchone()
            if result:
                seat_id = result[0]
                # Check if the seat is already reserved for the screening
                cursor.execute("SELECT * FROM BookingSeats WHERE SeatID = %s AND BookingID IN (SELECT BookingID FROM Bookings WHERE ScreeningID = %s)", (seat_id, screening_id))
                if cursor.fetchone():
                    raise Exception(f"Seat {seat_nb} is already booked for this screening.")
                cursor.execute("INSERT INTO BookingSeats (BookingID, SeatID) VALUES (%s, %s)",
                               (booking_id, seat_id))
            else:
                raise Exception(f"Seat {seat_nb} does not exist.")

        connection.commit()
        return 'Booking successful!'
    except mysql.connector.Error as e:
        connection.rollback()
        print(f"Error: {e}")
        return f'An error occurred with the booking: {e}'
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('index1'))

if __name__ == '__main__':
    app.run(debug=True)