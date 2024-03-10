

document.addEventListener('DOMContentLoaded', function() { /* Denna funktion används för att titta på dropdown-listan. Främsta syfte är att den har koll på screeningID för att kunna visa vilka platser som är bokade givet film/vilken screen */
    // Välj dropdown-listan
    var screeningDropdown = document.getElementById('screening_id');

    // Lyssnar efter förändringar i dropdown-listan
    screeningDropdown.addEventListener('change', function() {
        // Hämatar screeningID från dropdown-listan
        var screeningId = this.value; // this refererar till screeningDropdown

        // anropa funktionen som rensar alla valda platser, om det finns bokade platser. 
        clearSeatSelections();

        // anropa funktionen som hämtar bokade platser för vald screening
        fetchBookedSeats(screeningId);
    });
});

function clearSeatSelections() {
    // Hämatar alla platser
    var seats = document.querySelectorAll('.seat input[type="checkbox"]');
    
    // Loop igenom alla platser och sätt dem som aktiverade och ej valda. Detta är för att de inte ska ligga kvar några valda platser från tidigare vald screening.
    seats.forEach(function(seat) {
        seat.disabled = false; // Aktivera checkboxen
        seat.checked = false; // Avmarkera checkboxen
    });
}

function fetchBookedSeats(screeningId) { // Funktionen hämtar bokade platser för vald screening och sätter de som är valda som inaktiverade.
    fetch(`/booked_seats/${screeningId}`)
    .then(response => response.json())
    .then(data => {
        if(data && data.booked_seats) {
            var bookedSeats = data.booked_seats;
            // Loop igenom alla bokade platser och sätt dem som valda och inaktiverade.
            bookedSeats.forEach(seatId => {
                var seatCheckbox = document.getElementById(`seat${seatId}`);
                if(seatCheckbox) {
                    seatCheckbox.disabled = true;
                    seatCheckbox.checked = true;
                }
            });
        }
    })
    .catch(error => console.error('Error:', error));
}


document.addEventListener('DOMContentLoaded', function() {

    const pathSegments = window.location.pathname.split('/'); // Delar upp URL:en i segment
    const movieIdIndex = pathSegments.findIndex(segment => segment === 'movie') + 1; // Hittar index för movieId
    const movieId = pathSegments[movieIdIndex]; // Hämtar movieId från URL

    // Denna fetch-anrop hämtar bilden för vald film och sätter den som thumbnail, den hämtar bilden från databasen och movieID från URL.
    fetch(`/movie_image/${movieId}`)
        .then(response => response.json()) 
        .then(data => {
            const movieThumbnail = document.getElementById('movie-thumbnail'); // Hämtar img-taggen med id movie-thumbnail från HTML
            movieThumbnail.src = data.url; // Sätter bilden som thumbnail för vald film som .src på img-taggen.
        })
        .catch(error => console.error('Error:', error)); // Om det blir fel så skrivs det ut i konsolen.
});




