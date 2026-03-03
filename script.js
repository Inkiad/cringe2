let catPosition = -100;

function moveCat() {
    var cat = document.getElementById('cat');
    var width = window.innerWidth;
    cat.style.marginLeft = catPosition + 'px';
    catPosition += 5;
    if (catPosition > width + 100) {
        cat.style.marginLeft = '-100px';
        catPosition = -100;
    }
}

addEventListener('load', function () {
    setInterval(moveCat, 35);
});
