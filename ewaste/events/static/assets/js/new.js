document.addEventListener("DOMContentLoaded", function () {
    const sliderMainImage = document.getElementById("product-main-image");
    const sliderImageList = document.querySelectorAll(".image-list");

    sliderImageList.forEach(image => {
        image.addEventListener("click", function () {
            sliderMainImage.src = this.src;
        });
    });
});
