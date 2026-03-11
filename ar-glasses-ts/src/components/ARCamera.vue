<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/**
 * COMPONENT PROPS
 * @prop mode - Switch between 'glasses' and 'contacts' UI/Logic branches.
 */
const props = defineProps<{
    mode: string,
    model?: string,
}>();

// --- 1. DOM Refs & UI State ---
const videoEl = ref<HTMLVideoElement | null>(null);
const canvasEl = ref<HTMLCanvasElement | null>(null);
const isLoading = ref(true);
const containerStyle = ref({ aspectRatio: '16 / 9' });

// --- 2. 3D & ML Pipeline Variables ---
let faceLandmarker: FaceLandmarker;
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let glassesMesh: THREE.Group | null = null;
let animationFrameId: number;

/** * targetObj: An invisible 3D anchor used to hold raw ML coordinates.
 * We 'Lerp' the visible mesh toward this object to smooth out tracking jitter.
 */
const targetObj = new THREE.Object3D();

// --- 3. Lifecycle Hooks ---

onMounted(async () => {
    try {
        await initWebcam();
        await initMediaPipe();
        initThreeJS();

        handleResize(); // Sync canvas size with video feed
        window.addEventListener('resize', handleResize);

        await loadGlassesModel(props.model ?? 'classic_nerd_black');
        isLoading.value = false;
        renderLoop();
    } catch (error) {
        console.error('AR Initialization failed:', error);
    }
});

onUnmounted(() => {
    cancelAnimationFrame(animationFrameId);
    window.removeEventListener('resize', handleResize);

    // Stop the webcam stream to save power/privacy
    if (videoEl.value && videoEl.value.srcObject) {
        const stream = videoEl.value.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
    }

    if (renderer) renderer.dispose();
    if (faceLandmarker) faceLandmarker.close();
});

/** * UI WATCHER: Manages visibility of 3D assets when switching tabs.
 */
watch(() => props.mode, (newMode) => {
    if (newMode === 'contacts') {
        if (glassesMesh) glassesMesh.visible = false;
    } else if (newMode === 'glasses') {
        if (glassesMesh) glassesMesh.visible = true;
    }
});

// Watch for model changes and reload the GLB when requested
watch(() => props.model, async (newModel, oldModel) => {
    if (newModel && newModel !== oldModel) {
        try {
            await loadGlassesModel(newModel);
        } catch (err) {
            console.error('Failed to load model:', newModel, err);
        }
    }
});

// --- 4. Initialization Functions ---

/** * Requests camera access and sets up the mirrored user feed.
 */
async function initWebcam() {
    if (!videoEl.value) throw new Error('Video element not found');

    const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
    });
    videoEl.value.srcObject = stream;

    return new Promise<void>((resolve) => {
        videoEl.value!.onloadedmetadata = () => {
            const w = videoEl.value!.videoWidth;
            const h = videoEl.value!.videoHeight;
            containerStyle.value.aspectRatio = `${w} / ${h}`;
            videoEl.value!.play();
            resolve();
        };
    });
}

/** * Initializes the MediaPipe Face Landmarker with GPU acceleration.
 */
async function initMediaPipe() {
    const vision = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm',
    );
    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath: '/models/face_landmarker.task',
            delegate: 'GPU',
        },
        outputFaceBlendshapes: false, // Turned off to prevent errors with older task models
        runningMode: 'VIDEO',
        numFaces: 1,
    });
}

/** * Bootstraps the Three.js scene and lighting.
 */
function initThreeJS() {
    if (!canvasEl.value || !videoEl.value) return;
    const width = videoEl.value.videoWidth;
    const height = videoEl.value.videoHeight;

    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 2; // Offset camera to view the face at Z=0

    renderer = new THREE.WebGLRenderer({ canvas: canvasEl.value, alpha: true, antialias: true });
    renderer.setSize(width, height);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
    directionalLight.position.set(0, 5, 5);
    scene.add(directionalLight);
}

/** * Loads the glasses GLB and injects an 'Occlusion Head'.
 * The occlusion head is an invisible sphere that hides the glasses' arms 
 * when they pass behind your real ears.
 */
async function unloadGlassesModel() {
    if (!glassesMesh || !scene) return;
    scene.remove(glassesMesh);

    glassesMesh.traverse((child: any) => {
        if (child.isMesh) {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach((m: any) => m.dispose && m.dispose());
                } else if (child.material.dispose) {
                    child.material.dispose();
                }
            }
        }
    });

    glassesMesh = null;
}

async function loadGlassesModel(modelName: string) {
    // If another model is loaded, remove it first
    await unloadGlassesModel();

    const loader = new GLTFLoader();
    
    let path = modelName;
    if (!path.startsWith('/')) path = `/${path}`;
    if (!path.endsWith('.glb')) path = `${path}.glb`;

    return new Promise<void>((resolve, reject) => {
        loader.load(
            path,
            (gltf) => {
                glassesMesh = gltf.scene;

                // Create the invisible depth-mask head
                const headGeometry = new THREE.SphereGeometry(0.08, 32, 32);
                const occlusionMaterial = new THREE.MeshBasicMaterial({ colorWrite: false });
                const occlusionHead = new THREE.Mesh(headGeometry, occlusionMaterial);

                occlusionHead.scale.set(0.9, 1.4, 1.4);
                occlusionHead.position.set(0, 0, -0.11);
                occlusionHead.renderOrder = -1; // Render first to 'cut' the depth buffer

                glassesMesh.add(occlusionHead);
                scene.add(glassesMesh);
                resolve();
            },
            undefined,
            (err) => {
                console.error('GLTFLoader error for', path, err);
                reject(err);
            },
        );
    });
}

// --- 5. Render & Tracking Loop ---

let lastVideoTime = -1;

function renderLoop() {
    animationFrameId = requestAnimationFrame(renderLoop);

    // Only run ML if the camera has produced a new frame
    if (videoEl.value && videoEl.value.currentTime !== lastVideoTime) {
        lastVideoTime = videoEl.value.currentTime;

        const startTimeMs = performance.now();
        const results = faceLandmarker.detectForVideo(videoEl.value, startTimeMs);

        if (results.faceLandmarks && results.faceLandmarks.length > 0) {
            const landmarks = results.faceLandmarks[0];

            // --- BRANCH A: GLASSES TRACKING ---
            if (props.mode === 'glasses' && glassesMesh) {
                // Primary tracking points (MediaPipe index mapping)
                const nose = landmarks?.[168];     // Mid-nose bridge
                const leftTemple = landmarks?.[234]; // Left outer face
                const rightTemple = landmarks?.[454]; // Right outer face

                if (!nose || !leftTemple || !rightTemple) return;

                // Frustum Math: Convert 0-1 normalized coordinates to 3D world space
                const dist = camera.position.z;
                const vFov = camera.fov * (Math.PI / 180);
                const visibleHeight = 2 * Math.tan(vFov / 2) * dist;
                const visibleWidth = visibleHeight * camera.aspect;

                // Map nose bridge to X/Y world coords
                const xWorld = (nose.x - 0.5) * visibleWidth;
                const yWorld = -(nose.y - 0.5) * visibleHeight;
                targetObj.position.set(xWorld, yWorld, 0);

                // Calculate distances for Scale & Rotation
                const dx = leftTemple.x - rightTemple.x;
                const dy = leftTemple.y - rightTemple.y;
                const dz = leftTemple.z - rightTemple.z;

                // --- SCALE LOGIC ---
                // Math.hypot gets the absolute distance between temples
                const faceWidthNormalized = Math.hypot(dx, dy);
                const faceWidthWorld = faceWidthNormalized * visibleWidth;

                // 0.15 is the standard width of the GLB model in meters
                const exactScale = (faceWidthWorld / 0.15) * 1.15;
                targetObj.scale.set(exactScale, exactScale, exactScale);

                // --- ROTATION LOGIC ---
                // safeDx/Dy: We normalize for Mirror Mode to prevent the glasses 
                // from flipping upside down when the face mirrors.
                const safeDx = Math.abs(dx);
                const safeDy = dx < 0 ? -dy : dy;

                // DOUBLE-NEGATIVE MASTERSTROKE: Inverting both Z and Y rotation 
                // forces the glasses to match the mirrored webcam feed perfectly.
                const rollAngle = -Math.atan2(safeDy, safeDx); // Tilt (Roll)
                const yawAngle = -Math.atan2(dz, safeDx);    // Pan (Yaw)

                targetObj.rotation.z = rollAngle;
                targetObj.rotation.y = yawAngle;
            } 
            
            // --- BRANCH B: CONTACTS TRACKING (WIP) ---
            else if (props.mode === 'contacts') {
                // (TODO) Ready for Iris tracking points 473 and 468
            }
        } else if (glassesMesh) {
            // Hide glasses if no face is in view
            targetObj.position.set(0, 9999, 0);
        }
    }

    /** * LERP (Linear Interpolation) 
     * Glide the mesh 20% toward the target object every frame for smoothness.
     */
    if (glassesMesh && props.mode === 'glasses') {
        glassesMesh.position.lerp(targetObj.position, 0.2);
        glassesMesh.quaternion.slerp(targetObj.quaternion, 0.2);
        glassesMesh.scale.lerp(targetObj.scale, 0.2);
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

/** * Syncs the WebGL viewport with the container size on browser window resize.
 */
function handleResize() {
    if (!canvasEl.value || !camera || !renderer) return;
    const container = canvasEl.value.parentElement;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
}
</script>

<template>
    <div
        :style="containerStyle"
        class="relative w-full max-w-4xl mx-auto bg-neutral-900 overflow-hidden shadow-lg rounded-xl"
    >
        <div 
            v-if="props.mode === 'contacts'"
            class="absolute inset-0 z-20 flex items-center justify-center bg-black/60 backdrop-blur-md"
        >
            <h2 class="text-3xl font-bold text-white tracking-widest uppercase shadow-black drop-shadow-lg">
                Work in Progress
            </h2>
        </div>

        <video
            ref="videoEl"
            class="absolute inset-0 w-full h-full z-0"
            autoplay
            playsinline
            muted
        ></video>

        <canvas ref="canvasEl" class="absolute inset-0 w-full h-full z-10 pointer-events-none"></canvas>
    </div>
</template>