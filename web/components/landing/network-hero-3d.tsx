"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

const POINT_COUNT = 200;

function NetworkPoints() {
  const pointsRef = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(POINT_COUNT * 3);
    for (let i = 0; i < POINT_COUNT; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 6;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 6;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 6;
    }
    return arr;
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;
    pointsRef.current.rotation.y += 0.0015;
    pointsRef.current.rotation.x = state.pointer.y * 0.15;
    pointsRef.current.rotation.z = state.pointer.x * 0.1;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={POINT_COUNT}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial color="#2DD4BF" size={0.05} sizeAttenuation transparent opacity={0.8} />
    </points>
  );
}

export function NetworkHero3D() {
  return (
    <Canvas camera={{ position: [0, 0, 5], fov: 60 }} className="h-full w-full">
      <ambientLight intensity={0.5} />
      <NetworkPoints />
    </Canvas>
  );
}
