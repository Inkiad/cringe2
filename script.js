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

// ── Meow sounds ───────────────────────────────────────────────────────────────

const MEOWS_PET  = ['mew!', 'nyaa~', '*purr*', 'mrrp!', ':3', 'mew mew!', '♡'];
const MEOWS_GRAB = ['!!', 'heyyy!', 'mrrp!!', '>.<', 'noo!', '!!!!!'];
const MEOWS_RUN  = ['>:3', 'mrf.', 'bye!!', '...!', '!!'];
const MEOWS_IDLE = ['mrrrow...', '...', '*yawn*', 'mew.', 'hmm.'];

// ── State ─────────────────────────────────────────────────────────────────────

let catPosition    = -200;
let catInterval    = null;
let catGrabbed     = false;
let grabOffsetX    = 0;
let grabOffsetY    = 0;
let wiggleInterval = null;
let walkTick       = 0;
let walkFrame      = 0;
let wiggleFrame    = 0;

// Pet-vs-drag detection
let dragStartX     = null;
let dragStartY     = null;
let didDrag        = false;
let dragActive     = false;

// Bubble
let bubbleTimeout  = null;

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCat()    { return document.getElementById('cat'); }
function getBubble() { return document.getElementById('cat-bubble'); }

function setCatText(text) {
    const cat = getCat();
    if (cat) cat.innerText = text;
}

function rand(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function showBubble(text) {
    const cat    = getCat();
    const bubble = getBubble();
    if (!cat || !bubble) return;

    const rect = cat.getBoundingClientRect();
    bubble.textContent = text;
    bubble.style.left  = (rect.left + 8) + 'px';
    bubble.style.top   = (rect.top - 26) + 'px';
    bubble.classList.add('show');

    clearTimeout(bubbleTimeout);
    bubbleTimeout = setTimeout(() => bubble.classList.remove('show'), 1500);
}

function updateBubblePos() {
    const cat    = getCat();
    const bubble = getBubble();
    if (!cat || !bubble || !bubble.classList.contains('show')) return;
    const rect = cat.getBoundingClientRect();
    bubble.style.left = (rect.left + 8) + 'px';
    bubble.style.top  = (rect.top - 26) + 'px';
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

        // Rare random meow while walking
        if (walkTick % 200 === 0 && Math.random() < 0.35) {
            showBubble(rand(MEOWS_IDLE));
        }
    }, 35);
}

// ── Grab ──────────────────────────────────────────────────────────────────────

function initGrab(e) {
    if (catGrabbed) return;
    e.preventDefault();
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    didDrag    = false;
    dragActive = true;
}

function grabCat(e) {
    if (catGrabbed) return;
    catGrabbed  = true;
    wiggleFrame = 0;

    clearInterval(catInterval);

    const cat  = getCat();
    const rect = cat.getBoundingClientRect();
    grabOffsetX = dragStartX - rect.left;
    grabOffsetY = dragStartY - rect.top;

    cat.style.bottom     = '';
    cat.style.marginLeft = '0';
    cat.style.left       = (e.clientX - grabOffsetX) + 'px';
    cat.style.top        = (e.clientY - grabOffsetY) + 'px';
    cat.style.cursor     = 'grabbing';

    setCatText(CAT_GRAB_A);
    showBubble(rand(MEOWS_GRAB));

    wiggleInterval = setInterval(() => {
        wiggleFrame ^= 1;
        setCatText(wiggleFrame ? CAT_GRAB_B : CAT_GRAB_A);
        updateBubblePos();
    }, 220);
}

function dragCat(e) {
    // Check if drag threshold crossed — initiate grab
    if (!catGrabbed && dragActive) {
        const dx = e.clientX - dragStartX;
        const dy = e.clientY - dragStartY;
        if (Math.sqrt(dx * dx + dy * dy) > 6) {
            didDrag = true;
            grabCat(e);
        }
    }

    if (!catGrabbed) return;
    const cat = getCat();
    cat.style.left = (e.clientX - grabOffsetX) + 'px';
    cat.style.top  = (e.clientY - grabOffsetY) + 'px';
    updateBubblePos();
}

function releaseCat() {
    if (!dragActive && !catGrabbed) return;

    dragStartX = null;
    dragActive = false;

    // Quick tap without dragging — pet the cat
    if (!didDrag && !catGrabbed) {
        showBubble(rand(MEOWS_PET));
        return;
    }

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

    showBubble(rand(MEOWS_RUN));

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

    cat.addEventListener('mousedown', initGrab);
    document.addEventListener('mousemove', dragCat);
    document.addEventListener('mouseup', releaseCat);

    startWalking();
});
