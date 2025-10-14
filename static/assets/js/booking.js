const container = document.querySelector(".container");
const seats = document.querySelectorAll(".row .seat:not(.sold)");
const count = document.getElementById("count");
const total = document.getElementById("total");
const movieSelect = document.getElementById("movie");
const bookTicketBtn = document.getElementById("book-ticket-btn");
const upiPaymentForm = document.getElementById("upi-payment-form");
const payNowBtn = document.getElementById("pay-now-btn");
const upiPaymentResult = document.getElementById("upi-payment-result");
const paymentMethod = document.getElementById("payment-method");
const upiFields = document.getElementById("upi-fields");
const cardFields = document.getElementById("card-fields");

populateUI();
let ticketPrice = +movieSelect.value;

function setMovieData(movieIndex, moviePrice) {
  localStorage.setItem("selectedMovieIndex", movieIndex);
  localStorage.setItem("selectedMoviePrice", moviePrice);
}

function updateSelectedCount() {
  const selectedSeats = document.querySelectorAll(".row .seat.selected");
  const seatsIndex = [...selectedSeats].map(seat => [...seats].indexOf(seat));
  localStorage.setItem("selectedSeats", JSON.stringify(seatsIndex));
  const selectedSeatsCount = selectedSeats.length;
  count.innerText = selectedSeatsCount;
  total.innerText = selectedSeatsCount * ticketPrice;
  setMovieData(movieSelect.selectedIndex, movieSelect.value);
}

function populateUI() {
  const selectedSeats = JSON.parse(localStorage.getItem("selectedSeats"));
  const soldSeats = JSON.parse(localStorage.getItem("soldSeats"));
  if (selectedSeats !== null && selectedSeats.length > 0) {
    seats.forEach((seat, index) => {
      if (selectedSeats.indexOf(index) > -1) {
        seat.classList.add("selected");
      }
    });
  }
  if (soldSeats !== null && soldSeats.length > 0) {
    seats.forEach((seat, index) => {
      if (soldSeats.indexOf(index) > -1) {
        seat.classList.add("sold");
      }
    });
  }
  const selectedMovieIndex = localStorage.getItem("selectedMovieIndex");
  if (selectedMovieIndex !== null) {
    movieSelect.selectedIndex = selectedMovieIndex;
  }
}

movieSelect.addEventListener("change", e => {
  ticketPrice = +e.target.value;
  setMovieData(e.target.selectedIndex, e.target.value);
  updateSelectedCount();
});

container.addEventListener("click", e => {
  if (e.target.classList.contains("seat") && !e.target.classList.contains("sold")) {
    e.target.classList.toggle("selected");
    updateSelectedCount();
  }
});

bookTicketBtn.addEventListener("click", () => {
  const selectedSeats = document.querySelectorAll(".row .seat.selected");
  if (selectedSeats.length > 0) {
    upiPaymentForm.style.display = 'block';
    bookTicketBtn.style.display = 'none';
  } else {
    alert("Please select at least one seat to book.");
  }
});

// Payment logic
payNowBtn.addEventListener("click", () => {
  const method = paymentMethod.value;
  if (method === "upi") {
    const upiId = document.getElementById("upi-id").value;
    if (!upiId) {
      alert("Please enter your UPI ID.");
      return;
    }
  } else if (method === "card") {
    const cardNumber = document.getElementById("card-number").value;
    const cardExpiry = document.getElementById("card-expiry").value;
    const cardCvv = document.getElementById("card-cvv").value;
    if (!cardNumber || !cardExpiry || !cardCvv) {
      alert("Please fill all card details.");
      return;
    }
  }

  upiPaymentResult.innerText = "Payment Successful! Thank you for booking.";
  bookTickets();
});

paymentMethod.addEventListener("change", () => {
  if (paymentMethod.value === "upi") {
    upiFields.style.display = "block";
    cardFields.style.display = "none";
  } else {
    upiFields.style.display = "none";
    cardFields.style.display = "block";
  }
});

function bookTickets() {
  const selectedSeats = document.querySelectorAll(".row .seat.selected");
  selectedSeats.forEach(seat => {
    seat.classList.remove("selected");
    seat.classList.add("sold");
  });

  const soldSeatsIndex = [...document.querySelectorAll(".row .seat.sold")].map(
    seat => [...seats].indexOf(seat)
  );
  localStorage.setItem("soldSeats", JSON.stringify(soldSeatsIndex));
  localStorage.removeItem("selectedSeats");

  updateSelectedCount();
  alert("Tickets booked successfully!");
  upiPaymentForm.style.display = 'none';
  bookTicketBtn.style.display = 'block';
}

document.getElementById("reset-btn").addEventListener("click", () => {
  localStorage.removeItem("soldSeats");
  seats.forEach(seat => seat.classList.remove("sold"));
  localStorage.removeItem("selectedSeats");
  updateSelectedCount();
});
updateSelectedCount();
