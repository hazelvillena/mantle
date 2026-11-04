import { OrbitControls } from "@react-three/drei";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { mergeVertices, toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { Hardware } from "./types";

const SCALE = 0.01;

const FINISH: Record<string, string> = {
  "matte-white": "#f4f1ea",
  "matte-black": "#2a2a2a",
  "soft-gray": "#b9b6ae",
};

function viewTarget(center: [number, number, number]) {
  const [x, y, z] = center;
  return new THREE.Vector3(y * SCALE, -x * SCALE, z * SCALE);
}

function Mesh({
  url,
  color,
  opacity = 1,
  metalness = 0.08,
}: {
  url: string;
  color: string;
  opacity?: number;
  metalness?: number;
}) {
  const loaded = useLoader(STLLoader, url);
  const geometry = useMemo(() => {
    const welded = mergeVertices(loaded, 1e-4);
    const smooth = toCreasedNormals(welded, Math.PI / 6);
    welded.dispose();
    return smooth;
  }, [loaded]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        metalness={metalness}
        roughness={0.42}
        flatShading={false}
        side={THREE.DoubleSide}
        transparent={opacity < 1}
        opacity={opacity}
        depthWrite={opacity > 0.9}
      />
    </mesh>
  );
}

function Aim({
  hardware,
  frame,
}: {
  hardware: Hardware;
  frame: number;
}) {
  const camera = useThree((state) => state.camera);
  const controls = useThree((state) => state.controls) as unknown as
    | { target: THREE.Vector3; update: () => void }
    | null;
  const seen = useRef(-1);
  useEffect(() => {
    if (!controls || seen.current === frame) return;
    const target = viewTarget(hardware.center);
    controls.target.copy(target);
    camera.position.copy(target.clone().add(new THREE.Vector3(3.15, 1.7, 2.35)));
    controls.update();
    seen.current = frame;
  }, [camera, controls, frame, hardware.center]);
  return null;
}

function Assembly({
  hardware,
  parts,
  previousParts = [],
  finish,
  ghost,
  pose,
  showHardware,
  showExterior,
  showKeep,
}: {
  hardware: Hardware;
  parts: { name: string; url: string }[];
  previousParts?: { name: string; url: string }[];
  finish: string;
  ghost: boolean;
  pose: "extended" | "folded";
  showHardware: boolean;
  showExterior: boolean;
  showKeep: boolean;
}) {
  const pivot = hardware.pivot;
  const degrees = pose === "folded" ? 50 : 0;
  const base = FINISH[finish] ?? FINISH["matte-white"];
  const secondary = finish === "matte-black" ? "#3c3c3c" : finish === "soft-gray" ? "#a7a49c" : "#e3dfd6";
  return (
    <group scale={SCALE} rotation={[0, 0, -Math.PI / 2]}>
      {showKeep && (
        <mesh position={hardware.keepOut.center as [number, number, number]}>
          <boxGeometry args={hardware.keepOut.size as [number, number, number]} />
          <meshBasicMaterial color="#c4553a" wireframe transparent opacity={0.85} />
        </mesh>
      )}
      <group position={pivot} rotation={[THREE.MathUtils.degToRad(degrees), 0, 0]}>
        <group position={pivot.map((value) => -value) as [number, number, number]}>
          {showHardware && (
            <Mesh url={hardware.mesh} color="#b7b4ad" metalness={0.28} />
          )}
          {showExterior &&
            previousParts.map((part) => (
              <Mesh key={`prev-${part.url}`} url={part.url} color="#8d8b84" opacity={0.2} />
            ))}
          {showExterior &&
            parts.map((part) => (
              <Mesh
                key={part.url}
                url={part.url}
                color={part.name === "panel-a" || part.name === "body" ? base : secondary}
                opacity={ghost ? 0.22 : 1}
              />
            ))}
        </group>
      </group>
    </group>
  );
}

export function Stage({
  hardware,
  parts,
  previousParts,
  finish,
  pose,
  showHardware,
  showExterior,
  ghost,
  showKeep,
  frame,
}: {
  hardware: Hardware;
  parts: { name: string; url: string }[];
  previousParts: { name: string; url: string }[];
  finish: string;
  pose: "extended" | "folded";
  showHardware: boolean;
  showExterior: boolean;
  ghost: boolean;
  showKeep: boolean;
  frame: number;
}) {
  const reduce =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const target = viewTarget(hardware.center);
  return (
    <Canvas camera={{ position: [4.1, 1.9, 3.1], fov: 30 }} dpr={[1, 1.75]}>
      <color attach="background" args={["#121210"]} />
      <hemisphereLight args={["#f7f4ee", "#2a2a28", 1.15]} />
      <ambientLight intensity={0.45} />
      <directionalLight position={[5, 7, 4]} intensity={2.2} />
      <directionalLight position={[-4, 2, -3]} intensity={0.7} />
      <directionalLight position={[0, -4, 2]} intensity={0.45} />
      <Suspense fallback={null}>
        <Assembly
          hardware={hardware}
          parts={parts}
          previousParts={previousParts}
          finish={finish}
          ghost={ghost}
          pose={pose}
          showHardware={showHardware}
          showExterior={showExterior}
          showKeep={showKeep}
        />
      </Suspense>
      <Aim hardware={hardware} frame={frame} />
      <OrbitControls makeDefault enableDamping={!reduce} target={target.toArray()} />
    </Canvas>
  );
}
