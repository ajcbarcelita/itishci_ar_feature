<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// --- 1. DOM Refs & UI State ---
const videoEl = ref<HTMLVideoElement | null>(null);
const canvasEl = ref<HTMLCanvasElement | null>(null);
const isLoading = ref(true);

// Dynamically binds to the webcam's native aspect ratio to prevent coordinate drift
const containerStyle = ref({ aspectRatio: '16 / 9' });

// --- 2. 3D & ML Pipeline Variables ---
let faceLandmarker: FaceLandmarker;
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let glassesMesh: THREE.Group | null = null;
let animationFrameId: number;

// Target object used for Linear Interpolation (Lerp) to smooth out ML tracking jitter
const targetObj = new THREE.Object3D();

// --- 3. Lifecycle Hooks ---
onMounted(async () => {
    try {
        await initWebcam();
        await initMediaPipe();
        initThreeJS();

        // Initial sync of canvas size, then listen for window changes
        handleResize();
        window.addEventListener('resize', handleResize);

        await loadGlassesModel();
        isLoading.value = false;
        renderLoop();
    } catch (error) {
        console.error('AR Initialization failed:', error);
    }
});

onUnmounted(() => {
    cancelAnimationFrame(animationFrameId);
    window.removeEventListener('resize', handleResize);

    if (videoEl.value && videoEl.value.srcObject) {
        const stream = videoEl.value.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
    }

    if (renderer) renderer.dispose();
    if (faceLandmarker) faceLandmarker.close();
});

// --- 4. Initialization Functions ---
async function initWebcam() {
    if (!videoEl.value) throw new Error('Video element not found');

    const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
    });
    videoEl.value.srcObject = stream;

    return new Promise<void>((resolve) => {
        videoEl.value!.onloadedmetadata = () => {
            // Force the UI wrapper to match the raw video resolution perfectly
            const w = videoEl.value!.videoWidth;
            const h = videoEl.value!.videoHeight;
            containerStyle.value.aspectRatio = `${w} / ${h}`;

            videoEl.value!.play();
            resolve();
        };
    });
}

async function initMediaPipe() {
    const vision = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm',
    );
    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath: '/models/face_landmarker.task',
            delegate: 'GPU',
        },
        outputFaceBlendshapes: false,
        runningMode: 'VIDEO',
        numFaces: 1,
    });
}

function initThreeJS() {
    if (!canvasEl.value || !videoEl.value) return;
    const width = videoEl.value.videoWidth;
    const height = videoEl.value.videoHeight;

    scene = new THREE.Scene();

    // Setup camera frustum to match the video feed
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 2;

    renderer = new THREE.WebGLRenderer({ canvas: canvasEl.value, alpha: true, antialias: true });
    renderer.setSize(width, height);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
    directionalLight.position.set(0, 5, 5);
    scene.add(directionalLight);
}

async function loadGlassesModel() {
    const loader = new GLTFLoader();
    return new Promise<void>((resolve, reject) => {
        loader.load(
            '/models/test_glasses.glb',
            (gltf) => {
                glassesMesh = gltf.scene;

                // --- Occlusion Mask Setup ---
                // Generates an invisible depth-mask to hide the glasses arms behind the wearer's ears
                const headGeometry = new THREE.SphereGeometry(0.08, 32, 32);
                const occlusionMaterial = new THREE.MeshBasicMaterial({ colorWrite: false });
                const occlusionHead = new THREE.Mesh(headGeometry, occlusionMaterial);

                // Shape the mask to roughly match a human skull (narrower sides, deeper back)
                occlusionHead.scale.set(0.9, 1.4, 1.4);
                // Recess the mask into the Z-plane so it does not clip the front lenses
                occlusionHead.position.set(0, 0, -0.11);

                // Render order -1 ensures the invisible mask is drawn before the glasses
                occlusionHead.renderOrder = -1;

                glassesMesh.add(occlusionHead);
                scene.add(glassesMesh);
                resolve();
            },
            undefined,
            reject,
        );
    });
}

// --- 5. Render & Tracking Loop ---
let lastVideoTime = -1;

function renderLoop() {
    animationFrameId = requestAnimationFrame(renderLoop);

    // Only process ML inference if the video frame has advanced
    if (videoEl.value && videoEl.value.currentTime !== lastVideoTime) {
        lastVideoTime = videoEl.value.currentTime;

        const startTimeMs = performance.now();
        const results = faceLandmarker.detectForVideo(videoEl.value, startTimeMs);

        if (results.faceLandmarks && results.faceLandmarks.length > 0 && glassesMesh) {
            const landmarks = results.faceLandmarks[0];

            // Core facial tracking points
            const nose = landmarks?.[168];
            const leftTemple = landmarks?.[234];
            const rightTemple = landmarks?.[454];

            // Type guard against missing landmark data
            if (!nose || !leftTemple || !rightTemple) return;

            // Calculate exact physical bounds of the camera frustum at Z=0
            const dist = camera.position.z;
            const vFov = camera.fov * (Math.PI / 180);
            const visibleHeight = 2 * Math.tan(vFov / 2) * dist;
            const visibleWidth = visibleHeight * camera.aspect;

            // --- Calculate Position ---
            // Map normalized MediaPipe coordinates [0..1] to the 3D world bounds
            const xWorld = (nose.x - 0.5) * visibleWidth;
            const yWorld = -(nose.y - 0.5) * visibleHeight;
            targetObj.position.set(xWorld, yWorld, 0);

            // --- Calculate Scale ---
            const faceWidthNormalized = leftTemple.x - rightTemple.x;
            const faceWidthWorld = faceWidthNormalized * visibleWidth;

            // Divide by native GLB width (0.15m) and multiply by 1.15 for ergonomic fit
            const exactScale = (faceWidthWorld / 0.15) * 1.15;
            targetObj.scale.set(exactScale, exactScale, exactScale);

            // --- Calculate Rotation ---
            const dx = leftTemple.x - rightTemple.x;
            const dy = leftTemple.y - rightTemple.y;
            const dz = leftTemple.z - rightTemple.z;

            const rollAngle = Math.atan2(dy, dx);
            const yawAngle = Math.atan2(dz, dx);

            targetObj.rotation.z = rollAngle;
            targetObj.rotation.y = yawAngle;
        } else if (glassesMesh) {
            // Hide glasses off-screen if tracking is lost
            targetObj.position.set(0, 9999, 0);
        }
    }

    // --- Lerp Smoothing ---
    // Glides the 3D mesh 20% toward the mathematical target per frame to eliminate jitter
    if (glassesMesh) {
        glassesMesh.position.lerp(targetObj.position, 0.2);
        glassesMesh.quaternion.slerp(targetObj.quaternion, 0.2);
        glassesMesh.scale.lerp(targetObj.scale, 0.2);
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

// --- 6. Event Handlers ---
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
        class="relative w-full max-w-4xl mx-auto bg-neutral-900 overflow-hidden shadow-lg"
    >
        <video
            ref="videoEl"
            class="absolute inset-0 w-full h-full z-0"
            autoplay
            playsinline
            muted
        ></video>

        <canvas ref="canvasEl" class="absolute inset-0 w-full h-full z-10"></canvas>
    </div>
</template>
