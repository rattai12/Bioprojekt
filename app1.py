from flask import Flask, request, render_template, jsonify
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
def mainpage():
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT MovieID, Title, ThumbnailURL FROM Movies ORDER BY MovieID")
    movies = [{'MovieID': row[0], 'Title': row[1], 'ThumbnailURL': row[2]} for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    print("Movies:", movies)  # Print movies
    return render_template('mainpage.html', movies=movies)

@app.route('/movie/<int:movie_id>')
def movie_details(movie_id):
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT Title FROM Movies WHERE MovieID = %s", (movie_id,))
    movie_title = cursor.fetchone()[0]
    cursor.execute("""
        SELECT ScreeningID, Timeslot
        FROM Screenings
        WHERE MovieID = %s
        ORDER BY Timeslot
    """, (movie_id,))
    screenings = [{'ScreeningID': row[0], 'Timeslot': row[1].strftime('%Y-%m-%d %H:%M')} for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    print("Movie Title:", movie_title)  # Print movie title
    print("Screenings:", screenings)  # Print screenings
    return render_template('booking_page.html', movie_title=movie_title, screenings=screenings)

@app.route('/available_seats/<int:screening_id>')
def available_seats(screening_id):
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT Seats.SeatID, Seats.SeatNb, Seats.Status
        FROM Seats
        LEFT JOIN BookingSeats ON Seats.SeatID = BookingSeats.SeatID
        LEFT JOIN Bookings ON BookingSeats.BookingID = Bookings.BookingID
        WHERE Bookings.ScreeningID = %s OR Bookings.ScreeningID IS NULL
    """, (screening_id,))

    seats = [{'SeatID': row[0], 'SeatNb': row[1], 'Status': row[2]} for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    return jsonify(seats=seats)

@app.route('/booking_page')
def index():
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT Screenings.ScreeningID, Movies.Title, Screenings.Timeslot
        FROM Screenings
        JOIN Movies ON Screenings.MovieID = Movies.MovieID
        ORDER BY Movies.Title, Screenings.Timeslot
    """)
    screenings = [{
        'ScreeningID': row[0],
        'Title': row[1],
        'Timeslot': row[2].strftime('%Y-%m-%d %H:%M')
    } for row in cursor.fetchall()]
    cursor.execute("SELECT SeatID, SeatNb, Status FROM Seats")
    seats = [{'SeatID': row[0], 'SeatNb': row[1], 'Status': row[2]} for row in cursor.fetchall()]
    print("Screenings:", screenings)  # Print screenings
    print("Seats:", seats)  # Print seats
    cursor.close()
    connection.close()
    return render_template('booking_page.html', screenings=screenings, seats=seats)

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    email = request.form['email']
    phone_nb = request.form['phoneNb']
    screening_id = request.form['screening_id']
    seat_ids = request.form.getlist('seat_ids')

    selected_seats = []
    for key in request.form.keys():
        if key.startswith('seat'):
            # Check if the checkbox was selected
            if 'on' == request.form[key]:
                # Extract the seat ID from the name (e.g., 'seat1' -> '1')
                seat_id = key.replace('seat', '')
                selected_seats.append(int(seat_id))
            
    print(f"Selected seats: {selected_seats}")

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

        cursor.execute("INSERT INTO Bookings (CustomerID, ScreeningID) VALUES (%s, %s)",
                       (customer_id, screening_id))
        booking_id = cursor.lastrowid

        # Use selected_seats for booking instead of seat_ids
        for seat_id in selected_seats:  # Assuming selected_seats are the actual IDs needed
            # Verify if the seat is already booked for the screening
            cursor.execute("SELECT * FROM BookingSeats WHERE SeatID = %s AND ScreeningID = %s", (seat_id, screening_id))
            if cursor.fetchone():
                raise Exception(f"Seat {seat_id} is already booked for this screening.")
            # Insert into BookingSeats
            cursor.execute("INSERT INTO BookingSeats (BookingID, SeatID, ScreeningID) VALUES (%s, %s, %s)",
                           (booking_id, seat_id, screening_id))

        connection.commit()
        return jsonify(message='Booking successful!', booked_seats=selected_seats)  # Return booked seats information
    except mysql.connector.Error as e:
        connection.rollback()
        print(f"Error: {e}")
        return jsonify(message=f'An error occurred with the booking: {e}')
    finally:
        cursor.close()
        connection.close()



if __name__ == '__main__':
    app.run(debug=True)