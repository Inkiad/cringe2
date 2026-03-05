// ── Cat ASCII frames ──────────────────────────────────────────────────────────

// Two walk frames — legs and tail alternate to give a scamper feel
const CAT_WALK_A =
`    \\    /\\ \n` +
`     )  (')\n` +
`    (  /  )\n` +
`     \\(__)|`;

const CAT_WALK_B =
`    /    /\\ \n` +
`     )  (')\n` +
`    (  \\  )\n` +
`     /(__)| `;

// Held by tail — long tail, body hangs below, squirms between frames
const CAT_GRAB_A =
`      |    \n` +
`      |    \n` +
`     ~|    \n` +
`   __/|    \n` +
`  /      \\ \n` +
`  ( >o<  ) \n` +
`  (  ___) ) \n` +
`   \\____/  `;

const CAT_GRAB_B =
`      |    \n` +
`      |    \n` +
`      |~   \n` +
`      |\\__ \n` +
`  /      \\ \n` +
`  (  >o< ) \n` +
`  ( (___  ) \n` +
`   \\____/  `;

// Two run frames — faster leg alternation
const CAT_RUN_A =
`    \\    /\\ \n` +
`     )  ("> \n` +
`    ( //   )\n` +
`     \\(__)~ `;

const CAT_RUN_B =
`    /    /\\ \n` +
`     )  ("> \n` +
`    (   \\\\)\n` +
`     >(__)~ `;

// ── State ─────────────────────────────────────────────────────────────────────

let catPosition    = -200;
let catInterval    = null;
let catGrabbed     = false;
let everGrabbed    = false;   // once grabbed and released, cat is gone
let grabOffsetX    = 0;
let grabOffsetY    = 0;
let wiggleInterval = null;
let walkTick       = 0;
let walkFrame      = 0;
let wiggleFrame    = 0;

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

    walkTick  = 0;
    walkFrame = 0;
    setCatText(CAT_WALK_A);
    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';
    cat.style.cursor     = 'grab';

    catInterval = setInterval(() => {
        catPosition += 5;
        if (catPosition > window.innerWidth + 150) catPosition = -150;
        cat.style.marginLeft = catPosition + 'px';

        // Alternate walk frame every 7 ticks (~245ms) — leisurely pace
        walkTick++;
        if (walkTick % 7 === 0) {
            walkFrame ^= 1;
            setCatText(walkFrame ? CAT_WALK_B : CAT_WALK_A);
        }
    }, 35);
}

// ── Grab ──────────────────────────────────────────────────────────────────────

function grabCat(e) {
    if (catGrabbed) return;
    e.preventDefault();

    clearInterval(catInterval);
    catGrabbed   = true;
    everGrabbed  = true;
    wiggleFrame  = 0;

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

    // Drop to floor at current horizontal position, scramble off-screen
    catPosition = rect.left;
    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';
    cat.style.cursor     = 'default';

    let runTick = 0;
    let speed   = 22;
    const scramble = setInterval(() => {
        catPosition += speed;
        cat.style.marginLeft = catPosition + 'px';
        if (speed > 6) speed -= 0.35;

        // Alternate run frames faster than walk
        runTick++;
        if (runTick % 4 === 0) {
            setCatText(runTick % 8 === 0 ? CAT_RUN_A : CAT_RUN_B);
        }

        if (catPosition > window.innerWidth + 150) {
            clearInterval(scramble);
            // Cat is gone — it does not come back
            cat.style.display = 'none';
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
