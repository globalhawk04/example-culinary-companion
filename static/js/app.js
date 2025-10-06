// FILE: static/js/app.js (Final, Resilient Version)

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. GET UI ELEMENTS ---
    const recordButton = document.getElementById('recordButton');
    const outputContainer = document.getElementById('output-container');
    // Note: We get cookbookButton here but check for its existence before using it.
    const cookbookButton = document.getElementById('cookbookButton'); 

    // --- 2. SETUP STATE ---
    let mediaRecorder;
    let socket;
    let finalTranscript = '';
    let appState = 'idle'; // valid states: idle, recording, stopping

    // --- 3. CORE FUNCTIONS ---

    function startStreaming() {
        if (appState !== 'idle') return;
        appState = 'recording';
        finalTranscript = '';

        // --- UI Updates on Start ---
        recordButton.textContent = 'Stop Recording';
        recordButton.classList.add('bg-red-500', 'hover:bg-red-600');
        recordButton.classList.remove('bg-green-500', 'hover:bg-green-600');
        // Safely disable the cookbook button if it exists
        if (cookbookButton) cookbookButton.disabled = true;
        outputContainer.innerHTML = `<div id="transcript-area" class="p-4 border-2 border-dashed rounded-lg min-h-[10rem]"><p class="text-gray-500">Connecting...</p></div>`;

        navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/transcribe_streaming`);

            socket.onopen = () => {
                console.log("WebSocket opened.");
                document.querySelector('#transcript-area p').textContent = 'Listening...';
                
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
                        socket.send(event.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    stream.getTracks().forEach(track => track.stop());
                    console.log("MediaRecorder stopped. Closing WebSocket.");
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.close();
                    }
                };
                
                mediaRecorder.start(250);
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const transcriptArea = document.getElementById('transcript-area');
                if (!transcriptArea) return;

                if (data.is_final) {
                    finalTranscript += data.transcript + ' ';
                    transcriptArea.innerHTML = `<p>${finalTranscript}</p>`;
                } else {
                    transcriptArea.innerHTML = `<p>${finalTranscript}<span class="text-gray-400">${data.transcript}</span></p>`;
                }
            };

       
            socket.onclose = () => {
                console.log("WebSocket connection closed. Saving transcript to database.");
                const text = finalTranscript.trim();
                
                if (text.length > 0) {
                    outputContainer.innerHTML = `<div class="text-center py-10"><p class="text-gray-500">Saving transcript...</p></div>`;

                    fetch('/transcripts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ full_text: text })
                    })
                    .then(response => {
                        if (response.ok) {
                            return response.text(); 
                        }
                        throw new Error('Server responded with an error.');
                    })

                    // FILE: static/js/app.js (The definitive .then() block)

                    .then(html => {
                        // A more robust way to inject HTML and process scripts/htmx
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const newContent = doc.body.firstChild; // Get the form element from the parsed HTML

                        // Clear the container and append the new, properly formed element
                        outputContainer.innerHTML = '';
                        outputContainer.appendChild(newContent);
                        
                        // Now that we've used proper DOM methods, htmx.process is far more likely to succeed.
                        if (window.htmx) {
                            console.log("HTMX found. Processing new content in #output-container.");
                            htmx.process(outputContainer);
                        } else {
                            console.error("FATAL: HTMX library not found. Form will not be AJAX-ified.");
                        }
                        
                        resetUI();
                    })
                    .catch(error => {
                        console.error("Error saving transcript or rendering editor:", error);
                        outputContainer.innerHTML = `<p class="text-red-500">Error saving transcript to the database.</p>`;
                        resetUI();
                    });
                } else {
                    resetUI();
                    outputContainer.innerHTML = `<div class="text-center py-10"><p class="text-gray-500">No speech detected. Click "Start Talking" to try again.</p></div>`;
                }
            };

        }).catch(err => {
            console.error("Failed to initialize recording:", err);
            outputContainer.innerHTML = `<p class="text-red-500">Error: Could not start recording. Please grant microphone permissions.</p>`;
            resetUI();
        });
    }

    function stopStreaming() {
        if (appState !== 'recording' || !mediaRecorder) return;
        
        appState = 'stopping';
        recordButton.textContent = 'Processing...';
        recordButton.disabled = true;

        mediaRecorder.stop();
    }
    
    function resetUI() {
        appState = 'idle';
        recordButton.disabled = false;
        recordButton.textContent = 'Start Talking';
        recordButton.classList.remove('bg-red-500', 'hover:bg-red-600');
        recordButton.classList.add('bg-green-500', 'hover:bg-green-600');
        if (cookbookButton) cookbookButton.disabled = false;
    }

    // --- 4. ATTACH EVENT LISTENERS ---

    // Ensure the record button exists before adding a listener
    if (recordButton) {
        recordButton.addEventListener('click', () => {
            if (appState === 'idle') {
                startStreaming();
            } else if (appState === 'recording') {
                stopStreaming();
            }
        });
    } else {
        console.error("Fatal Error: Record button not found on page load.");
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // ... all your existing code (startStreaming, etc.) ...

    // --- 5. GLOBAL HTMX EVENT LISTENER ---
    // This is the most robust way to ensure HTMX works on content
    // that is swapped in multiple times.
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Find the newly swapped-in content
        const newContent = event.detail.elt;
        
        // Check if there are any forms inside the new content
        if (newContent.querySelector('form') || newContent.matches('form')) {
            console.log('HTMX afterSwap event detected on new form. Processing elements.');
            htmx.process(newContent);
        }
    });
});