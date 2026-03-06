import cv2
import mediapipe as mp
import numpy as np
import trimesh
import pyrender
import time


class AR3DGlasses:
    def __init__(self, model_path, task_path="face_landmarker.task"):

        # User adjustments (FACE SPACE)
        self.offset = np.array([0.0, -0.03, -0.08])  # x, y, z
        self.scale = 1.0

        # MediaPipe Face Landmarker
        base_options = mp.tasks.BaseOptions(model_asset_path=task_path)
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

        # Load + FIX model orientation
        mesh = trimesh.load(model_path, force="mesh")

        # Flip model forward (GLB → MediaPipe space)
        flip = np.eye(4)
        flip[2, 2] = -1   # flip Z
        mesh.apply_transform(flip)

        self.mesh = pyrender.Mesh.from_trimesh(mesh)

        # Scene
        self.scene = pyrender.Scene(
            bg_color=[0, 0, 0, 0],
            ambient_light=[0.6, 0.6, 0.6]
        )
        self.node = self.scene.add(self.mesh)

        # Light
        light = pyrender.DirectionalLight(color=[1, 1, 1], intensity=2.5)
        self.scene.add(light, pose=np.eye(4))

        # Renderer
        self.width, self.height = 640, 480
        self.renderer = pyrender.OffscreenRenderer(self.width, self.height)

        # Camera
        camera = pyrender.IntrinsicsCamera(
            fx=600, fy=600,
            cx=self.width // 2,
            cy=self.height // 2
        )
        self.scene.add(camera, pose=np.eye(4))

    def apply_transform(self, face_matrix):
        # SCALE (local)
        scale_mtx = np.eye(4)
        scale_mtx[:3, :3] *= self.scale

        # TRANSLATE (local face space)
        translate_mtx = np.eye(4)
        translate_mtx[:3, 3] = self.offset

        # Correct order
        local = translate_mtx @ scale_mtx
        return face_matrix @ local

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(3, self.width)
        cap.set(4, self.height)

        print("""
            Controls:
            W / S : Up / Down
            A / D : Forward / Back
            J / L : Left / Right
            + / - : Scale
            Q     : Quit
            """)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            timestamp = int(time.time() * 1000)
            result = self.landmarker.detect_for_video(mp_image, timestamp)

            if result.facial_transformation_matrixes:
                face_matrix = np.array(
                    result.facial_transformation_matrixes[0].data
                ).reshape(4, 4)

                pose = self.apply_transform(face_matrix)
                self.scene.set_pose(self.node, pose)

                color, _ = self.renderer.render(
                    self.scene,
                    flags=pyrender.RenderFlags.RGBA
                )

                alpha = color[:, :, 3] / 255.0
                for c in range(3):
                    frame[:, :, c] = (
                        alpha * color[:, :, c]
                        + (1 - alpha) * frame[:, :, c]
                    )

            cv2.imshow("AR 3D Glasses", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("w"):
                self.offset[1] += 0.02
            elif key == ord("s"):
                self.offset[1] -= 0.02
            elif key == ord("a"):
                self.offset[2] += 0.02
            elif key == ord("d"):
                self.offset[2] -= 0.02
            elif key == ord("j"):
                self.offset[0] -= 0.02
            elif key == ord("l"):
                self.offset[0] += 0.02
            elif key in (ord("+"), ord("=")):
                self.scale *= 1.05
            elif key == ord("-"):
                self.scale *= 0.95

        cap.release()
        cv2.destroyAllWindows()
        self.renderer.delete()


if __name__ == "__main__":
    app = AR3DGlasses("glasses_centered.glb")
    app.run()
