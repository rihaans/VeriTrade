document.addEventListener("DOMContentLoaded", function () {
    const balance = document.getElementById("credits-balance");
    const dropdown = document.getElementById("pay-dropdown");

    balance.addEventListener("click", function () {
        dropdown.classList.toggle("hidden");
    });

    document.getElementById("pay-button").addEventListener("click", function () {
        alert("Payment successful!");
        // Add logic to update the database here if needed
    });
});