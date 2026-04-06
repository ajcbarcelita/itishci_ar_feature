<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

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

const CONTACT_LENS_OPACITY = 0.35;

/**
 * EAR (Eye Aspect Ratio) threshold — below this value the eye is considered closed.
 * Tune between 0.15–0.22 depending on how sensitive you want it.
 */
const EAR_THRESHOLD = 0.18;

/**
 * Smooth the EAR value over time so rapid blinks don't cause flicker.
 * 0 = no smoothing, 1 = never changes. 0.35 is a good balance.
 */
const EAR_SMOOTHING = 0.35;
let smoothedLeftEAR = 0.3;
let smoothedRightEAR = 0.3;

/**
 * Per-eye opacity targets — lenses fade in/out instead of popping.
 * This makes blinking look much more natural.
 */
let leftLensOpacity = CONTACT_LENS_OPACITY;
let rightLensOpacity = CONTACT_LENS_OPACITY;
const OPACITY_FADE_SPEED = 0.18; 

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

                    const planeW = isContacts ? 0.077 : 0.35;
                    const planeH = isContacts ? 0.077 : 0.35;
                    const geom = new THREE.PlaneGeometry(planeW, planeH);

                    const contactMaterialOptions: THREE.MeshBasicMaterialParameters = {
                        map: texture,
                        transparent: true,
                        opacity: isContacts ? CONTACT_LENS_OPACITY : 1,
                        alphaTest: isContacts ? 0.02 : 0,
                        depthWrite: !isContacts,
                    };

                    const matL = new THREE.MeshBasicMaterial(contactMaterialOptions);
                    const left = new THREE.Mesh(geom, matL);
                    left.position.set(isContacts ? 0 : -0.045, 0, 0);

                    const matR = new THREE.MeshBasicMaterial(contactMaterialOptions);
                    const right = new THREE.Mesh(geom, matR);
                    right.position.set(isContacts ? 0 : 0.045, 0, 0);

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

// --- 5. EAR Helper ---

/**
 * Computes Eye Aspect Ratio for one eye.
 *
 * Uses 6 landmark points arranged as:
 *
 *        p2  p3
 *   p1            p4
 *        p6  p5
 *
 * EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
 *
 * When the eye is open, EAR ≈ 0.25–0.35.
 * When closed, EAR drops below ~0.18.
 *
 */
function computeEAR(
    landmarks: { x: number; y: number; z: number }[],
    p1i: number, p2i: number, p3i: number,
    p4i: number, p5i: number, p6i: number,
): number {
    const p1 = landmarks[p1i];
    const p2 = landmarks[p2i];
    const p3 = landmarks[p3i];
    const p4 = landmarks[p4i];
    const p5 = landmarks[p5i];
    const p6 = landmarks[p6i];

    if (!p1 || !p2 || !p3 || !p4 || !p5 || !p6) return 0.3; // default open

    const v1 = Math.hypot(p2.x - p6.x, p2.y - p6.y);
    const v2 = Math.hypot(p3.x - p5.x, p3.y - p5.y);
    const h  = Math.hypot(p1.x - p4.x, p1.y - p4.y);

    if (h < 1e-6) return 0.3;
    return (v1 + v2) / (2.0 * h);
}

// --- 6. Render & Tracking Loop ---

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
                if ((glassesMesh as any).userData?.isImageLenses && props.mode === 'contacts') {
                    glassesMesh.visible = true;
                }

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
                    const leftIris  = landmarks?.[468];
                    const rightIris = landmarks?.[473];
                    const leftMesh  = (glassesMesh as any).userData.leftMesh  as THREE.Mesh;
                    const rightMesh = (glassesMesh as any).userData.rightMesh as THREE.Mesh;

                    if (leftIris && rightIris && leftMesh && rightMesh) {
                        // --- Position ---
                        const lx = (leftIris.x - 0.5) * visibleWidth;
                        const ly = -(leftIris.y - 0.5) * visibleHeight;
                        const rx = (rightIris.x - 0.5) * visibleWidth;
                        const ry = -(rightIris.y - 0.5) * visibleHeight;

                        leftMesh.position.lerp(new THREE.Vector3(lx, ly, 0), 0.4);
                        rightMesh.position.lerp(new THREE.Vector3(rx, ry, 0), 0.4);

                        // --- Scale ---
                        const dx = leftIris.x - rightIris.x;
                        const faceWidthNormalized = Math.abs(dx);
                        const scaleFactor = Math.max(0.9, faceWidthNormalized * 3.0);
                        leftMesh.scale.lerp(new THREE.Vector3(scaleFactor, scaleFactor, scaleFactor), 0.5);
                        rightMesh.scale.lerp(new THREE.Vector3(scaleFactor, scaleFactor, scaleFactor), 0.5);

                        // --- EAR: detect eye open/closed per eye ---
                        // Left eye landmarks:  p1=33, p2=160, p3=158, p4=133, p5=153, p6=144
                        // Right eye landmarks: p1=362, p2=385, p3=387, p4=263, p5=373, p6=380
                        const rawLeftEAR  = computeEAR(landmarks,  33, 160, 158, 133, 153, 144);
                        const rawRightEAR = computeEAR(landmarks, 362, 385, 387, 263, 373, 380);

                        // Smooth EAR so micro-jitter doesn't cause flicker
                        smoothedLeftEAR  = smoothedLeftEAR  * EAR_SMOOTHING + rawLeftEAR  * (1 - EAR_SMOOTHING);
                        smoothedRightEAR = smoothedRightEAR * EAR_SMOOTHING + rawRightEAR * (1 - EAR_SMOOTHING);

                        const leftTarget  = smoothedLeftEAR  > EAR_THRESHOLD ? CONTACT_LENS_OPACITY : 0;
                        const rightTarget = smoothedRightEAR > EAR_THRESHOLD ? CONTACT_LENS_OPACITY : 0;

                        leftLensOpacity  += (leftTarget  - leftLensOpacity)  * OPACITY_FADE_SPEED;
                        rightLensOpacity += (rightTarget - rightLensOpacity) * OPACITY_FADE_SPEED;

                        // Apply opacity — also hide mesh entirely when fully transparent
                        // to avoid any residual rendering cost
                        (leftMesh.material  as THREE.MeshBasicMaterial).opacity = leftLensOpacity;
                        (rightMesh.material as THREE.MeshBasicMaterial).opacity = rightLensOpacity;
                        leftMesh.visible  = leftLensOpacity  > 0.01;
                        rightMesh.visible = rightLensOpacity > 0.01;
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
                    const yawAngle  = -Math.atan2(dz, safeDx);

                    targetObj.rotation.z = rollAngle;
                    targetObj.rotation.y = yawAngle;
                }
            }
        } else if (glassesMesh) {
            if ((glassesMesh as any).userData?.isImageLenses && props.mode === 'contacts') {
                // Fade out both lenses when face is lost
                leftLensOpacity  *= (1 - OPACITY_FADE_SPEED);
                rightLensOpacity *= (1 - OPACITY_FADE_SPEED);

                const leftMesh  = (glassesMesh as any).userData.leftMesh  as THREE.Mesh;
                const rightMesh = (glassesMesh as any).userData.rightMesh as THREE.Mesh;
                (leftMesh.material  as THREE.MeshBasicMaterial).opacity = leftLensOpacity;
                (rightMesh.material as THREE.MeshBasicMaterial).opacity = rightLensOpacity;
                leftMesh.visible  = leftLensOpacity  > 0.01;
                rightMesh.visible = rightLensOpacity > 0.01;

                if (leftLensOpacity <= 0.01 && rightLensOpacity <= 0.01) {
                    glassesMesh.visible = false;
                }
            } else {
                targetObj.position.set(0, 9999, 0);
            }
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