// ── Cat ASCII frames ──────────────────────────────────────────────────────────

const CAT_WALK =
`    \\    /\\ \n` +
`     )  (')\n` +
`    (  /  )\n` +
`     \\(__)|`;

// Held by tail — squirms between two frames
const CAT_GRAB_A =
`      |    \n` +
`    _/|    \n` +
`  ( >o< )  \n` +
`  (     )  \n` +
`   \\___/   `;

const CAT_GRAB_B =
`      |    \n` +
`      |\\_  \n` +
`  ( >o< )  \n` +
`  (     )  \n` +
`   /___\\   `;

// Scrambling away after release
const CAT_RUN =
`    \\    /\\ \n` +
`     )  ("> \n` +
`    (  z  ) \n` +
`     \\(__)~ `;

// ── State ─────────────────────────────────────────────────────────────────────

let catPosition  = -200;
let catInterval  = null;
let catGrabbed   = false;
let grabOffsetX  = 0;
let grabOffsetY  = 0;
let wiggleInterval = null;
let wiggleFrame  = 0;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCat() { return document.getElementById('cat'); }

function setCatText(text) {
    const cat = getCat();
    if (cat) cat.innerText = text;
}

// ── Walking ───────────────────────────────────────────────────────────────────

function startWalking() {
    const cat = getCat();
    if (!cat) return;

    setCatText(CAT_WALK);
    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';
    cat.style.cursor     = 'grab';

    catInterval = setInterval(() => {
        catPosition += 5;
        if (catPosition > window.innerWidth + 150) catPosition = -150;
        cat.style.marginLeft = catPosition + 'px';
    }, 35);
}

// ── Grab ──────────────────────────────────────────────────────────────────────

function grabCat(e) {
    if (catGrabbed) return;
    e.preventDefault();

    clearInterval(catInterval);
    catGrabbed = true;
    wiggleFrame = 0;

    const cat  = getCat();
    const rect = cat.getBoundingClientRect();
    grabOffsetX = e.clientX - rect.left;
    grabOffsetY = e.clientY - rect.top;

    cat.style.bottom     = '';
    cat.style.marginLeft = '0';
    cat.style.left       = (e.clientX - grabOffsetX) + 'px';
    cat.style.top        = (e.clientY - grabOffsetY) + 'px';
    cat.style.cursor     = 'grabbing';

    setCatText(CAT_GRAB_A);

    wiggleInterval = setInterval(() => {
        wiggleFrame ^= 1;
        setCatText(wiggleFrame ? CAT_GRAB_B : CAT_GRAB_A);
    }, 220);
}

function dragCat(e) {
    if (!catGrabbed) return;
    const cat = getCat();
    cat.style.left = (e.clientX - grabOffsetX) + 'px';
    cat.style.top  = (e.clientY - grabOffsetY) + 'px';
}

function releaseCat() {
    if (!catGrabbed) return;
    catGrabbed = false;
    clearInterval(wiggleInterval);

    const cat  = getCat();
    const rect = cat.getBoundingClientRect();

    // Drop to floor and scramble off to the right
    catPosition = rect.left;
    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';
    cat.style.cursor     = 'grab';

    setCatText(CAT_RUN);

    let speed = 20;
    const scramble = setInterval(() => {
        catPosition += speed;
        cat.style.marginLeft = catPosition + 'px';
        if (speed > 5) speed -= 0.4;
        if (catPosition > window.innerWidth + 150) {
            catPosition = -150;
            clearInterval(scramble);
            startWalking();
        }
    }, 35);
}

// ── Init ──────────────────────────────────────────────────────────────────────

addEventListener('load', () => {
    const cat = getCat();
    if (!cat) return;

    cat.addEventListener('mousedown', grabCat);
    document.addEventListener('mousemove', dragCat);
    document.addEventListener('mouseup', releaseCat);

    startWalking();
});
