from flask import Flask, request, render_template, jsonify, redirect, flash
import mysql.connector
from mysql.connector import pooling
import time



app = Flask(__name__)
app.secret_key = 'hemliga_passowrdet!'

dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "Rotmos3718!",
    "database": "test2"
}

cnx_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **dbconfig) 

@app.route('/') # Denna funktion kopplar ihop med databasen och hämtar alla filmer, samt deras thumbnailURL. ThumbnailURL visas på hemsidan med hjälp av en bildhost. 
def mainpage():
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT MovieID, Title, ThumbnailURL FROM Movies ORDER BY MovieID")
    movies = [{'MovieID': row[0], 'Title': row[1], 'ThumbnailURL': row[2]} for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    print("Movies:", movies)  #Skriv ut filmer, för debugging
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


@app.route('/movie_image/<int:movie_id>')
def movie_image(movie_id):
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT ThumbnailURL FROM Movies WHERE MovieID = %s", (movie_id,))
    thumbnail_url = cursor.fetchone()[0]
    cursor.close()
    connection.close()
    print("Thumbnail URL:", thumbnail_url)  # Print thumbnail URL
    return jsonify(url=thumbnail_url)






@app.route('/booked_seats/<int:screening_id>') #Denna funktion kopplar ihop med databasen och hämtar alla bokade platser för en specifik film. med hjälp av ScreeningID så kan man hantera att samma stolar blir bokade till olika filmer och tidpunkter.
def booked_seats(screening_id):
    connection = cnx_pool.get_connection()
    cursor = connection.cursor()
    booked_seats = [] #Skapar en tom lista för att fylla med bokade platser.

    cursor.execute("""
        SELECT bookingseats.SeatID
        FROM bookingseats
        WHERE bookingseats.ScreeningID = %s
    """, (screening_id,))

    for row in cursor.fetchall(): #För varje rad i resultatet från SQL frågan så läggs raden till i listan booked_seats.
        booked_seats.append(row[0])

    cursor.close()
    connection.close()
    print(booked_seats)
    return jsonify(booked_seats=booked_seats) #Returnerar bokade platser för en specifik film i JSON format. 

@app.route('/booking_page') #Denna funktion kopplar ihop med databasen och hämtar alla filmer, samt deras thumbnailURL. ThumbnailURL visas på hemsidan med hjälp av en bildhost.
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
    print("Screenings:", screenings)  # Print screenings, for debugging
    cursor.close()
    connection.close()
    return render_template('booking_page.html', screenings=screenings)

@app.route('/book', methods=['POST']) #Denna funktion används för att boka en film. Funktionen tar in namn, email, telefonnummer, screening_id och valda platser som input från forumläret på webbsidan.  
#Funktionen kopplar ihop med databasen och lägger till en ny kund i Customers tabellen om kunden inte redan finns. Sedan läggs en ny bokning till i Bookings tabellen.
def book():
    name = request.form['name']
    email = request.form['email']
    phone_nb = request.form['phoneNb']
    screening_id = request.form['screening_id']
    

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
        connection.start_transaction() # Starta en transaktion för att säkerställa att allt går rätt till. annars rollback.
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
        flash('Booking successful!', 'success')
    except mysql.connector.Error as e:
        connection.rollback()
        print(f"Error: {e}")
        flash(f'An error occurred with the booking: {str(e)}', 'error')
        
    finally:
        cursor.close()
        connection.close()  
       # time.sleep(1)
        return redirect('/')
    
@app.route('/delete_bookings', methods=['POST']) #Denna funktion används för att avboka platser, den tar email som input och avbokar dessa platser för kunden med det email som skickas in.
def delete_bookings():
    email = request.form['email']  # Assuming email is sent in the form data

    connection = cnx_pool.get_connection()
    cursor = connection.cursor()

    try:
        # Koppla ihop med databasen
        connection.start_transaction()

        # Hämta CustomerID för email
        cursor.execute("SELECT CustomerID FROM Customers WHERE Email = %s", (email,))
        customer_result = cursor.fetchone()
        if not customer_result:
            return jsonify(message="No customer found with the given email"), 404
        customer_id = customer_result[0]

        # Hämta kundens bokningar
        cursor.execute("SELECT BookingID FROM Bookings WHERE CustomerID = %s", (customer_id,))
        booking_ids = [row[0] for row in cursor.fetchall()]

        # Ta bort bokningar från BookingSeats med hjälp av BookingID
        for booking_id in booking_ids:
            cursor.execute("DELETE FROM BookingSeats WHERE BookingID = %s", (booking_id,))

        
        connection.commit()
        flash('Booking cancelled!', 'success')
    except mysql.connector.Error as e:
        # Rollback ifall något går snett. Skriv ut felmeddelande.
        connection.rollback()
        return jsonify(message=f"An error occurred: {e}"), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/cancel_booking') #Renderar sidan för att avboka bokningar
def delete_form():
    # Rendera formulär för att avboka bokning
    return render_template('cancel_booking.html')

@app.route('/about')
def about_page():
    # Rendera about-sidan
    return render_template('about_page.html')






if __name__ == '__main__': #Starta appen, debug=True för att kunna se ändringar utan att behöva starta om servern. 
    app.run(debug=True)