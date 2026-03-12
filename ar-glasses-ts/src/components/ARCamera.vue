<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/**
 * COMPONENT PROPS
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

/** targetObj: An invisible 3D anchor used to hold raw ML coordinates */
const targetObj = new THREE.Object3D();

// --- 3. Lifecycle Hooks ---

onMounted(async () => {
    try {
        await initWebcam();
        await initMediaPipe();
        initThreeJS();

        handleResize();
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

    if (videoEl.value && videoEl.value.srcObject) {
        const stream = videoEl.value.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
    }

    if (renderer) renderer.dispose();
    if (faceLandmarker) faceLandmarker.close();
});

watch(() => props.mode, () => {
    if (glassesMesh) glassesMesh.visible = true;
});

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
                    if (child.material.map && child.material.map.dispose) child.material.map.dispose();
                    child.material.dispose();
                }
            }
        }
    });

    glassesMesh = null;
}

async function loadGlassesModel(modelName: string) {
    await unloadGlassesModel();

    let path = modelName;
    if (!path.startsWith('/')) path = `/${path}`;

    const isImage = path.toLowerCase().endsWith('.png') || path.toLowerCase().endsWith('.jpg') || path.toLowerCase().endsWith('.jpeg');

    if (isImage) {
        return new Promise<void>((resolve, reject) => {
            const texLoader = new THREE.TextureLoader();
            texLoader.load(
                path,
                (texture) => {
                    (texture as any).encoding = (THREE as any).sRGBEncoding;

                    const group = new THREE.Group();

                    const isContacts = props.mode === 'contacts';
                    
                    // Make contact planes larger for better coverage
                    const planeW = isContacts ? 0.08 : 0.35;
                    const planeH = isContacts ? 0.08 : 0.35;
                    const geom = new THREE.PlaneGeometry(planeW, planeH);

                    const matL = new THREE.MeshBasicMaterial({ map: texture, transparent: true });
                    const left = new THREE.Mesh(geom, matL);
                    left.position.set(isContacts ? 0 : -0.045, 0, 0); // Adjusted spacing for larger lenses

                    const matR = new THREE.MeshBasicMaterial({ map: texture, transparent: true });
                    const right = new THREE.Mesh(geom, matR);
                    right.position.set(isContacts ? 0 : 0.045, 0, 0); // Adjusted spacing for larger lenses

                    group.add(left);
                    group.add(right);

                    (group as any).userData = { isImageLenses: true, leftMesh: left, rightMesh: right };

                    glassesMesh = group;
                    scene.add(group);
                    resolve();
                },
                undefined,
                (err) => {
                    console.error('TextureLoader error for', path, err);
                    reject(err);
                },
            );
        });
    }

    const loader = new GLTFLoader();
    let glbPath = path;
    if (!glbPath.endsWith('.glb')) glbPath = `${glbPath}.glb`;

    return new Promise<void>((resolve, reject) => {
        loader.load(
            glbPath,
            (gltf) => {
                glassesMesh = gltf.scene;

                const headGeometry = new THREE.SphereGeometry(0.08, 32, 32);
                const occlusionMaterial = new THREE.MeshBasicMaterial({ colorWrite: false });
                const occlusionHead = new THREE.Mesh(headGeometry, occlusionMaterial);

                occlusionHead.scale.set(0.9, 1.4, 1.4);
                occlusionHead.position.set(0, 0, -0.11);
                occlusionHead.renderOrder = -1;

                glassesMesh.add(occlusionHead);
                scene.add(glassesMesh);
                resolve();
            },
            undefined,
            (err) => {
                console.error('GLTFLoader error for', glbPath, err);
                reject(err);
            },
        );
    });
}

// --- 5. Render & Tracking Loop ---

let lastVideoTime = -1;

function renderLoop() {
    animationFrameId = requestAnimationFrame(renderLoop);

    if (videoEl.value && videoEl.value.currentTime !== lastVideoTime) {
        lastVideoTime = videoEl.value.currentTime;

        const startTimeMs = performance.now();
        const results = faceLandmarker.detectForVideo(videoEl.value, startTimeMs);

        if (results.faceLandmarks && results.faceLandmarks.length > 0) {
            const landmarks = results.faceLandmarks[0];

            if (glassesMesh) {
                const nose = landmarks?.[168];
                const leftTemple = landmarks?.[234];
                const rightTemple = landmarks?.[454];

                if (!nose || !leftTemple || !rightTemple) return;

                const dist = camera.position.z;
                const vFov = camera.fov * (Math.PI / 180);
                const visibleHeight = 2 * Math.tan(vFov / 2) * dist;
                const visibleWidth = visibleHeight * camera.aspect;

                const xWorld = (nose.x - 0.5) * visibleWidth;
                const yWorld = -(nose.y - 0.5) * visibleHeight;
                targetObj.position.set(xWorld, yWorld, 0);

                // Contact Lens positioning
                if ((glassesMesh as any)?.userData?.isImageLenses && props.mode === 'contacts') {
                    const leftIris = landmarks?.[468];
                    const rightIris = landmarks?.[473];
                    const leftMesh = (glassesMesh as any).userData.leftMesh as THREE.Mesh;
                    const rightMesh = (glassesMesh as any).userData.rightMesh as THREE.Mesh;

                    if (leftIris && rightIris && leftMesh && rightMesh) {
                        const lx = (leftIris.x - 0.5) * visibleWidth;
                        const ly = -(leftIris.y - 0.5) * visibleHeight;
                        const rx = (rightIris.x - 0.5) * visibleWidth;
                        const ry = -(rightIris.y - 0.5) * visibleHeight;

                        leftMesh.position.lerp(new THREE.Vector3(lx, ly, 0), 0.4);
                        rightMesh.position.lerp(new THREE.Vector3(rx, ry, 0), 0.4);

                        const dx = leftIris.x - rightIris.x;
                        const faceWidthNormalized = Math.abs(dx);

                        // Increase multiplier so overlays scale larger relative to eye separation
                        const scaleFactor = Math.max(0.9, faceWidthNormalized * 3.0);
                        leftMesh.scale.lerp(new THREE.Vector3(scaleFactor, scaleFactor, scaleFactor), 0.5);
                        rightMesh.scale.lerp(new THREE.Vector3(scaleFactor, scaleFactor, scaleFactor), 0.5);
                    }
                } else {
                    const dx = leftTemple.x - rightTemple.x;
                    const dy = leftTemple.y - rightTemple.y;
                    const dz = leftTemple.z - rightTemple.z;

                    const faceWidthNormalized = Math.hypot(dx, dy);
                    const faceWidthWorld = faceWidthNormalized * visibleWidth;

                    const exactScale = (faceWidthWorld / 0.15) * 1.15;
                    targetObj.scale.set(exactScale, exactScale, exactScale);

                    const safeDx = Math.abs(dx);
                    const safeDy = dx < 0 ? -dy : dy;

                    const rollAngle = -Math.atan2(safeDy, safeDx);
                    const yawAngle = -Math.atan2(dz, safeDx);

                    targetObj.rotation.z = rollAngle;
                    targetObj.rotation.y = yawAngle;
                }
            }
        } else if (glassesMesh) {
            targetObj.position.set(0, 9999, 0);
        }
    }

    if (glassesMesh && !((glassesMesh as any).userData?.isImageLenses && props.mode === 'contacts')) {
        glassesMesh.position.lerp(targetObj.position, 0.2);
        glassesMesh.quaternion.slerp(targetObj.quaternion, 0.2);
        glassesMesh.scale.lerp(targetObj.scale, 0.2);
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera);
    }
}

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