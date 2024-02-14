from flask import Flask, jsonify, request
import mysql.connector
import json
from mysql.connector import Error
import pymysql.cursors
from http.server import SimpleHTTPRequestHandler, HTTPServer

app = Flask(__name__)

# Replace with your MySQL configuration details
connection = pymysql.connect(host='dsd400.port0.org',
                             user='dsd400',
                             password='krångligt_'.encode().decode('latin1'),
                             database='JeJeElSo',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


def get_db_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**config)
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

@app.route('/api/seats/available', methods=['GET'])
def get_available_seats():
    movie_id = request.args.get('movieId')
    timeslot = request.args.get('timeslot')
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    query = """
    SELECT * FROM Theater
    WHERE MovieID = %s AND Timeslot = %s AND AvailableSeats > 0
    """
    cursor.execute(query, (movie_id, timeslot))
    
    available_seats = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return jsonify(available_seats)

@app.route('/api/seats/book', methods=['POST'])
def book_seats():
    data = request.json
    customer_id = data['customerId']
    theater_id = data['theaterId']
    seat_numbers = data['seatNumbers']
    
    connection = get_db_connection()
    cursor = connection.cursor()

    # Begin a transaction
    connection.start_transaction()

    try:
        # Update Theater table to decrement the AvailableSeats
        update_query = """
        UPDATE Theater
        SET AvailableSeats = AvailableSeats - %s
        WHERE TheaterID = %s AND AvailableSeats >= %s
        """
        cursor.execute(update_query, (len(seat_numbers), theater_id, len(seat_numbers)))

        # Check if the seats were successfully decremented
        if cursor.rowcount == 0:
            raise Exception("Not enough available seats.")

        # Insert a new Booking record
        insert_query = """
        INSERT INTO Booking (CustomerID, TheaterID)
        VALUES (%s, %s)
        """
        cursor.execute(insert_query, (customer_id, theater_id))
        booking_id = cursor.lastrowid

        # Assuming there's a Seat table, update it as booked
        # This part of the logic depends on how you handle individual seat bookings
        # and is omitted for brevity.

        # Commit the transaction
        connection.commit()

        message = {'message': 'Booking successful', 'bookingId': booking_id}
        status_code = 200
    except Exception as e:
        # Rollback the transaction in case of any failure
        connection.rollback()
        message = {'error': str(e)}
        status_code = 400
    finally:
        cursor.close()
        connection.close()

    return jsonify(message), status_code

if __name__ == '__main__':
    app.run(debug=True)