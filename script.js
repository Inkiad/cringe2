// ── ASCII frame library ────────────────────────────────────────────────────────
//
// Naming: CAT_<STATE>_<VARIANT>   or   CAT_T_<FROM>2<TO>_<STEP>
//
// All idle/walk frames are 4 lines tall so they sit flush at bottom: 0.
// Grab frames are taller (cat hangs by tail) — positioned with top/left instead.

// ── Walk (existing) ───────────────────────────────────────────────────────────

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

// ── Grab / held (existing) ────────────────────────────────────────────────────

const CAT_GRAB_A =
`      |    \n` +
`      |    \n` +
`     ~|    \n` +
`   __/|    \n` +
`  /      \\ \n` +
`  ( >o<  ) \n` +
`  (  ___) )\n` +
`   \\____/  `;

const CAT_GRAB_B =
`      |    \n` +
`      |    \n` +
`      |~   \n` +
`      |\\__ \n` +
`  /      \\ \n` +
`  (  >o< ) \n` +
`  ( (___  )\n` +
`   \\____/  `;

// ── Run (existing) ────────────────────────────────────────────────────────────

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

// ── Sit ───────────────────────────────────────────────────────────────────────
// Side profile, facing right. Slow blink: A (open) ↔ B (half-closed).

const CAT_SIT_A =
`    /\\_    \n` +
`   ( '^)   \n` +
`   )    \\  \n` +
`  (_____)  `;

const CAT_SIT_B =
`    /\\_    \n` +
`   ( '-)   \n` +
`   )    \\  \n` +
`  (_____)  `;

// ── Loaf ──────────────────────────────────────────────────────────────────────
// Paws fully tucked, transitional state between sit and sleep.

const CAT_LOAF =
`    /\\_    \n` +
`   ( -.-) \n` +
`   )~~~~\\  \n` +
`  (_____)  `;

// ── Sleep ─────────────────────────────────────────────────────────────────────
// Curled, droopy head. B frame pops a small z bubble.

const CAT_SLEEP_A =
`    ,-\\_   \n` +
`   ( zzz)  \n` +
`   )~~~~\\  \n` +
`  (_____) `;

const CAT_SLEEP_B =
`    ,-\\_     \n` +
`   ( zzz) z\n` +
`   )~~~~\\  \n` +
`  (_____) `;

// ── Transition frames ─────────────────────────────────────────────────────────

// Walk → Sit, step 1: pause, glance back
const CAT_T_W2S_1 =
`     _   /\\ \n` +
`     )  (^')\n` +
`    (      )\n` +
`     \\(__)/ `;

// Walk → Sit, step 2: lower into sit
const CAT_T_W2S_2 =
`    /\\_    \n` +
`   ( ^'.)  \n` +
`   (    )  \n` +
`   (____) `;

// Sit → Walk: rising up off haunches
const CAT_T_S2W =
`    /\\_    \n` +
`   \\( '^) \n` +
`    ) --  )\n` +
`    \\(__)/ `;

// Stretch: front paw extended, used before resuming walk
const CAT_STRETCH =
`    /\\     \n` +
`   ('^)    \n` +
`   )    /--\n` +
`  (__)/    `;

// Loaf → Sleep: head nodding down
const CAT_T_L2S =
`    .,-\\_  \n` +
`   ( ....) \n` +
`   )~~~~\\  \n` +
`  (_____) `;

// Sleep → awake: head lifting
const CAT_WAKE =
`    /\\_    \n` +
`   ( ^.-)  \n` +
`   )~~~~\\  \n` +
`  (_____) `;

// ── Meow sounds ───────────────────────────────────────────────────────────────

const MEOWS_PET   = ['mew!', 'nyaa~', '*purr*', 'mrrp!', ':3', 'mew mew!', '♡'];
const MEOWS_GRAB  = ['!!', 'heyyy!', 'mrrp!!', '>.<', 'noo!', '!!!!!'];
const MEOWS_RUN   = ['>:3', 'mrf.', 'bye!!', '...!', '!!'];
const MEOWS_IDLE  = ['mrrrow...', '...', '*yawn*', 'mew.', 'hmm.'];
const MEOWS_SIT   = ['...', '*purr*', 'mew.', '(ᵕ·ᴗ·ᵕ)', 'hmm.'];
const MEOWS_SLEEP = ['zzz...', '*snore*', '...zz'];

// ── State machine ─────────────────────────────────────────────────────────────

const S = {
    WALK:  'walk',
    SIT:   'sit',
    SLEEP: 'sleep',
    TRANS: 'trans',
    GRAB:  'grab',
    RUN:   'run',
};

let catState    = S.WALK;
let catPosition = -200;
let catInterval = null;

// Walk
let walkTick  = 0;
let walkFrame = 0;

// Idle (sit / sleep)
let idleTick  = 0;
let idleFrame = 0;
let idleMax   = 0;

// Transition
let transQueue = [];  // [{ frame, dur }]
let transIdx   = 0;
let transTick  = 0;
let transNext  = S.WALK;

// Run
let runSpeed = 22;
let runTick  = 0;

// Grab / drag
let catGrabbed   = false;
let grabOffsetX  = 0;
let grabOffsetY  = 0;
let wiggleInterval = null;
let wiggleFrame  = 0;

let dragStartX = null;
let dragStartY = null;
let didDrag    = false;
let dragActive = false;

// Bubble
let bubbleTimeout = null;

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
    bubble.style.top  = (rect.top  - 26) + 'px';
}

// ── State entry ───────────────────────────────────────────────────────────────

function enterState(s) {
    catState  = s;
    idleTick  = 0;
    idleFrame = 0;
    const cat = getCat();
    if (!cat) return;

    switch (s) {
        case S.WALK:
            walkTick  = 0;
            walkFrame = 0;
            cat.style.cursor = 'grab';
            setCatText(CAT_WALK_A);
            break;
        case S.SIT:
            idleMax = 80 + Math.floor(Math.random() * 180);
            setCatText(CAT_SIT_A);
            break;
        case S.SLEEP:
            idleMax = 180 + Math.floor(Math.random() * 350);
            setCatText(CAT_SLEEP_A);
            break;
    }
}

function startTransition(frames, nextState) {
    catState   = S.TRANS;
    transQueue = frames;
    transIdx   = 0;
    transTick  = 0;
    transNext  = nextState;
    setCatText(frames[0].frame);
}

// ── Tick handlers ─────────────────────────────────────────────────────────────

function tickWalk() {
    catPosition += 5;
    // Wrap around to the left — cat never disappears
    if (catPosition > window.innerWidth + 150) catPosition = -200;

    const cat = getCat();
    if (cat) cat.style.marginLeft = catPosition + 'px';

    walkTick++;
    if (walkTick % 7 === 0) {
        walkFrame ^= 1;
        setCatText(walkFrame ? CAT_WALK_B : CAT_WALK_A);
    }

    // Rare idle meow
    if (walkTick % 200 === 0 && Math.random() < 0.35) {
        showBubble(rand(MEOWS_IDLE));
    }

    // Random sit after walking long enough
    if (walkTick > 160 && walkTick % 50 === 0 && Math.random() < 0.18) {
        startTransition([
            { frame: CAT_T_W2S_1, dur: 10 },
            { frame: CAT_T_W2S_2, dur: 10 },
        ], S.SIT);
    }
}

function tickSit() {
    idleTick++;

    // Slow blink (~3 s)
    if (idleTick % 85 === 0) {
        idleFrame ^= 1;
        setCatText(idleFrame ? CAT_SIT_B : CAT_SIT_A);
    }

    // Occasional thought bubble
    if (idleTick % 110 === 0 && Math.random() < 0.4) {
        showBubble(rand(MEOWS_SIT));
    }

    if (idleTick >= idleMax) {
        if (Math.random() < 0.5) {
            // Stand back up and walk
            startTransition([
                { frame: CAT_T_S2W,   dur: 10 },
                { frame: CAT_STRETCH, dur: 14 },
            ], S.WALK);
        } else {
            // Settle into sleep
            startTransition([
                { frame: CAT_LOAF,  dur: 40 },
                { frame: CAT_T_L2S, dur: 20 },
            ], S.SLEEP);
        }
    }
}

function tickSleep() {
    idleTick++;

    // Z-bubble every ~2 s
    if (idleTick % 55 === 0) {
        idleFrame ^= 1;
        setCatText(idleFrame ? CAT_SLEEP_B : CAT_SLEEP_A);
    }

    if (idleTick % 140 === 0 && Math.random() < 0.5) {
        showBubble(rand(MEOWS_SLEEP));
    }

    if (idleTick >= idleMax) {
        startTransition([
            { frame: CAT_WAKE,    dur: 20 },
            { frame: CAT_T_S2W,   dur: 10 },
            { frame: CAT_STRETCH, dur: 14 },
        ], S.WALK);
    }
}

function tickTransition() {
    transTick++;
    const cur = transQueue[transIdx];
    if (transTick >= cur.dur) {
        transTick = 0;
        transIdx++;
        if (transIdx >= transQueue.length) {
            enterState(transNext);
            return;
        }
        setCatText(transQueue[transIdx].frame);
    }
}

function tickRun() {
    catPosition += runSpeed;
    if (runSpeed > 6) runSpeed -= 0.35;

    const cat = getCat();
    if (cat) cat.style.marginLeft = catPosition + 'px';

    runTick++;
    if (runTick % 4 === 0) {
        setCatText(runTick % 8 === 0 ? CAT_RUN_A : CAT_RUN_B);
    }

    // Once off-screen, wrap to the left and start walking again
    if (catPosition > window.innerWidth + 150) {
        catPosition = -200;
        enterState(S.WALK);
    }
}

// ── Main tick ─────────────────────────────────────────────────────────────────

function mainTick() {
    switch (catState) {
        case S.WALK:  tickWalk();       break;
        case S.SIT:   tickSit();        break;
        case S.SLEEP: tickSleep();      break;
        case S.TRANS: tickTransition(); break;
        case S.RUN:   tickRun();        break;
        case S.GRAB:  /* wiggle handled by wiggleInterval */ break;
    }
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
    catState    = S.GRAB;

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

    // Quick tap — pet
    if (!didDrag && !catGrabbed) {
        showBubble(rand(MEOWS_PET));
        return;
    }

    if (!catGrabbed) return;
    catGrabbed = false;
    clearInterval(wiggleInterval);

    const cat  = getCat();
    const rect = cat.getBoundingClientRect();

    catPosition = rect.left;
    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';
    cat.style.cursor     = 'grab';

    showBubble(rand(MEOWS_RUN));

    runSpeed = 22;
    runTick  = 0;
    catState = S.RUN;
    setCatText(CAT_RUN_A);
}

// ── Init ──────────────────────────────────────────────────────────────────────

addEventListener('load', () => {
    const cat = getCat();
    if (!cat) return;

    cat.style.bottom     = '0';
    cat.style.top        = '';
    cat.style.left       = '';
    cat.style.marginLeft = catPosition + 'px';

    cat.addEventListener('mousedown', initGrab);
    document.addEventListener('mousemove', dragCat);
    document.addEventListener('mouseup', releaseCat);

    enterState(S.WALK);
    catInterval = setInterval(mainTick, 35);
});
