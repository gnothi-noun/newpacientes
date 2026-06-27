**Go for Space Applications: From Desktop Simulation to Bare-Metal Execution and Legacy Model Migration**

**WHITTINGSLOW Patricio (1)(a), SELLANES Juan(2)(b)**

(1) Instituto Tecnológico de Buenos Aires, Ciudad de Buenos Aires, Argentina\
(2) Instituto Gulich, Universidad Nacional de Córdoba – CONAE, Córdoba, Argentina\
(a) graded.sp@gmail.com · (b) juan.sellanes@ig.edu.ar



# Abstract

As aerospace programs compress schedules and phase out legacy code, teams need a language that combines C-class runtime performance, Python-class development speed, and a single-stack path from desktop simulation to embedded flight hardware. We present practical, experience-driven evidence that Go (Golang) satisfies these requirements across four contributions. First, we port a restricted three body Earth–Moon transfer trajectory solver from NumPy-optimized Python to Go, achieving up to 200× speedup and collapsing parameter sweeps from weeks to hours. Second, we demonstrate embedded viability: TinyGo produces jitter-free binaries competitive with C on ARM Cortex-M targets; in the extreme case, compiling without a garbage collector yields a footprint smaller than the equivalent bare-C binary. TamaGo compiles a full UEFI environment including an SSH server in under 10 MB with no RTOS or C-shim. Third, we present a source-to-source Fortran 90 transpiler that migrates heritage aerodynamic and propulsion models into testable Go modules, surfacing latent defects invisible to existing Fortran compilers including argument-count mismatches, stack corruption, and control-flow defects in NASA GEODYN orbit-determination software. Fourth, we present `gnco`, a pure-Go flight dynamics toolkit whose RKN12(10) integrator exploits the second-order structure of the equations of motion to achieve near-machine-precision energy conservation at step sizes of 300 s. We close with a candid discussion of allocation discipline, garbage-collector management, and the gaps that remain before Go can be considered for safety-critical flight qualification.



# Introduction

Go (Golang) is a statically typed, compiled programming language designed at Google by Robert Griesemer, Rob Pike, and Ken Thompson; the latter credited with the original design of the C programming language [@gospec2024]. Work began in 2007, motivated in part by multi-hour C++ build times on large Google codebases [@pike2012]. The language was released as open source in November 2009 and reached the stable 1.0 milestone in March 2012, since which it has maintained a cadence of two feature releases per year together with a strict backward-compatibility guarantee. The specification fits in approximately 100 pages, a compactness that emerged from the designers' consensus rule: no feature was added unless all three authors agreed it belonged in the language.

Aerospace software engineering today is often fragmented across incompatible languages. Python dominates rapid analysis and trajectory simulation because its scientific ecosystem (NumPy, SciPy, Astropy) lowers the barrier to numerical work and its interactive tooling accelerates exploration. C and C++ dominate flight software because they offer predictable performance, mature qualification toolchains, and direct hardware access. Fortran persists in heritage mathematical models such as orbital mechanics, atmospheric models, and propulsion tables, that encode decades of institutional knowledge and have proven too expensive or too risky to rewrite. The result is a stack where the prototype and the product are written in different languages, with different numerical libraries, by teams whose tools, idioms, and workflows do not overlap.

This fragmentation is not merely an inconvenience. Software interface failures are a documented cause of mission loss in aerospace: the Ariane 501 flight failure was traced to a 64-bit floating-point value being truncated to a 16-bit integer across a software boundary in the inertial reference system [@ariane1996]. Whether teams maintain parallel implementations or bridge them via language bindings, the verification burden multiplies. And the context-switching cost between Python's dynamic dispatch and C's manual memory management is real: engineers fluent in one are rarely fluent in both, and the gap between them is where integration errors live.

Go offers a pragmatic path out of this fragmentation. A single language and toolchain can run a high-fidelity trajectory simulation on a workstation, execute a control loop on an ARM Cortex-M microcontroller via the TinyGo compiler [@tinygo2025], boot a UEFI environment on an application-class SoC via TamaGo [@barisani2025], and provide a mechanically checked migration path for Fortran heritage models. 

This paper presents practical, experience-driven evidence through four contributions:

1. **Performance**: a comparison of a Go trajectory solver against its NumPy-based Python reference, characterizing speedup as a function of integration step size.
2. **Embedded execution**: a survey of TinyGo and TamaGo, covering real-time behaviour, memory footprint, and deterministic allocation strategies.
3. **Fortran transpilation**: a source-to-source transpiler targeting a Fortran 90 subset, demonstrated on NASA GEODYN orbit-determination software.
4. **Flight dynamics toolkit**: `gnco`, a pure-Go library for 3-to-6-DoF simulation, whose RKN12(10) integrator achieves near-machine-precision energy conservation at large orbital step sizes without external numerical libraries.

We close with a discussion of engineering practices required to make Go dependable for aerospace use and the known gaps that limit its applicability today.

# Go Language Overview

Table 1 places Go against Python, C/C++, and Rust across dimensions relevant to aerospace software development.

| Feature | Go | Python | C / C++ | Rust |
| :--- | :---: | :---: | :---: | :---: |
| Development speed* | High | High | Low | Low |
| Runtime performance | High | Very Low | High | High |
| MCU embedded support | Yes | Limited | Yes | Yes |
| Static type safety | Yes | No | Partial | Yes |
| Garbage collector | Optional | Mandatory | None | None (RAII) |
| Build system | Built-in | Ecosystem | External | Built-in |
| Scientific ecosystem | Developing | Excellent | Good | Developing |
| Specification size | ~100 pages | N/A | ~1700 pages | ~400 pages |

: Qualitative comparison of languages relevant to aerospace software.

Several properties of Go are worth elaborating in the context of aerospace use.

**Static typing with inference.** Every variable has a compile-time type. The compiler rejects programs with unused variables or imports and enforces interface satisfaction statically. This eliminates a category of maintenance defects common in dynamically typed codebases and enables refactoring tools that can reason about the program without running it.

**Explicit error handling.** Go functions return errors as values rather than raising exceptions. This forces call sites to decide what to do with a failure before the program can proceed. There is no hidden control-flow path through an exception stack; every error-handling branch is visible in the source. NASA rules prohibit the use of exceptions in flight software [@markMaimone2014].

**Concurrency as a first-class primitive.** Goroutines are cooperatively scheduled, lightweight user-space threads. Channels provide typed, synchronized communication. The concurrency model composes predictably and is available with the same API both on desktop runtimes and on TinyGo-targeted microcontrollers, giving teams a uniform programming model from workstation simulation to flight computer.

**Tunable and optional garbage collection.** Go's garbage collector is a concurrent, tri-color mark-and-sweep implementation with sub-millisecond pause-time targets on current hardware [@hudson2018]. Two runtime parameters (`GOGC`, `GOMEMLIMIT`) give operators direct control over collection frequency and heap ceiling without recompilation. On TinyGo, the garbage collector is a conservative mark-and-sweep design; it can be disabled entirely for hard-determinism requirements, at which point the binary carries no runtime overhead whatsoever. A USB hello-world on the RP2040 compiled with `-gc=leaking -scheduler=none -panic=trap` produces a 14kB binary, versus 23kB for the equivalent C example [@picohello2025].

**Single-binary deployment.** A Go executable statically links all dependencies into a single binary with no dynamic library requirements, eliminating version mismatches at deployment which is a relevant property for long-duration missions where the software environment must be reproducible years after initial integration.


# Performance: Go vs. Python
Benchmarks were run on a 12th-generation Intel i5-12400F (6 cores / 12 threads, 4.4 GHz boost) under Linux.

## Single-Threaded Benchmark: GTO-to-Lunar Trajectory

The benchmark is a planar restricted three-body (Earth–Moon–cubesat) transfer simulation originally developed in Python for a feasibility study of a low-thrust lunar mission from GTO [@sellanes2025]. The program integrates the equations of motion for a cubesat equipped with a high-specific-impulse electric thruster, performing a series of orbit-raising maneuvers from GTO through GEO into lunar orbit. The Python implementation is approximately 320 lines and depends on NumPy for vector state representation and SciPy for numerical integration (an RKF45 adaptive integrator).

The Go reimplementation is 650 lines with no third-party dependencies. Of those, 330 lines replicate SciPy's RKF45 integrator and 8 lines replace NumPy's vector operations, leaving ~312 lines for the transfer logic itself. The Python program delegates this numerical work to compiled C extensions; the Go program implements it entirely in Go.

The structural difference becomes apparent when examining the rate functions (the user-supplied derivatives that the integrator evaluates at every step). In Python:

```python
def rates0(t, f):  # coast phase
    x, y, vx, vy, m = f
    r1_val = np.linalg.norm([x + pi_2 * r12, y])
    r2_val = np.linalg.norm([x - pi_1 * r12, y])
    r1_3 = r1_val**3;  r2_3 = r2_val**3
    ax = 2*W*vy + W**2*x - mu1*(x-x1)/r1_3 - mu2*(x-x2)/r2_3
    ay = -2*W*vx + W**2*y - (mu1/r1_3 + mu2/r2_3)*y
    return [vx, vy, ax, ay, 0]
```

The state is an untyped list `f` whose fields are accessed by position. Adding or reordering state variables silently corrupts results, the bug is invisible until the output is inspected. In Go:

```go
func RatesCoastEM(t float64, s State, phiS0 float64) (dPos, dVel Vec, dm float64) {
    x, y   := s.Pos.X, s.Pos.Y
    vx, vy := s.Vel.X, s.Vel.Y
    r1_3, r2_3 := gravity(x, y)
    ax := (2*W*vy + W*W*x) - mu1*(x-x1)/r1_3 - mu2*(x-x2)/r2_3
    ay := (-2*W*vx + W*W*y) - (mu1/r1_3+mu2/r2_3)*y
    dPos = s.Vel
    dVel = Vec{X: ax, Y: ay}
    return
}
```

Input and output types are explicit: rearranging or adding fields in `State` or `Vec` is safe, and any mismatch in the rate function signature is a compile-time error.

Table 2 reports CPU user time for six consecutive identical runs, selecting best Python and worst Go results to bound the comparison conservatively.

| Max step (s) | Python (s) | Go (s) | Speedup |
| ---: | ---: | ---: | ---: |
| 450 | 4.99 | 0.22 | 22.7× |
| 100 | 14.04 | 0.15 | 93.6× |
| 10 | 135.39 | 0.70 | 193.4× |
| 1 | 1360.91 | 6.87 | 198.1× |

: GTO-to-Lunar benchmark: CPU user time and speedup by maximum integration step size.

Speedup increases as step size decreases, plateauing near 200× at 10 s and below. The convergence is explained by the relative contribution of user-defined Python code vs. compiled NumPy/SciPy kernels: at large steps the integrator takes few steps, obscuring the per-step cost; at small steps the integrator calls the Python rate function millions of times, making dispatch overhead the bottleneck. Go executes the equivalent logic natively.

Numerical equivalence was prioritised over peak performance: an early prototype using a simpler integrator reached 450×, but faithfully replicating SciPy's adaptive step-selection logic brought this down to ~200×.

## Multi-Core Benchmark: SDF Shape Design

The second benchmark evaluates multi-threaded performance. The task is generating the STL mesh of a knurled cylinder from an implicit signed-distance field (SDF) definition. The workload is dominated by repeated transcendental function evaluation (cos, sin, sqrt).  The Python implementation uses the `fogleman/sdf` library, which internally parallelizes SDF evaluation over a voxel grid using NumPy batch operations distributed across worker processes:

```python
from sdf import *
f = rounded_cylinder(1, 0.1, 5)
x = box((1, 1, 4)).rotate(pi / 4)
x = x.circular_array(24, 1.6)
x = x.twist(0.75) | x.twist(-0.75)
f -= x.k(0.1)
f -= cylinder(0.5).k(0.1)
f.save('knurling.stl', step=0.01)
```

The equivalent Go program uses the `gsdf` library and mirrors the same geometry definition in Go syntax [@gsdfknurled2025]. Both programs parallelized across all available threads (12 workers / 11 goroutines respectively). Table 3 shows results.

| Language | Wall (s) | CPU (s) | Eval. (M) | M evals/s |
| :--- | ---: | ---: | ---: | ---: |
| Python | 9.41 | 36.03 | 32.43 | 0.344 |
| Go | 2.37 | 10.79 | 20.89 | 0.531 |
| **Speedup** | **3.97×** | **3.34×** | — | **1.54×** |

: SDF knurled-cylinder benchmark: wall time, CPU user time, and evaluation throughput.

The Go implementation is 54% faster in SDF evaluation throughput and 3.97× faster in wall time. The improvement is substantially smaller than in the trajectory benchmark. The reason is architectural: the `fogleman/sdf` library delegates all primitive and operator evaluation to NumPy vector operations that execute as compiled C loops over large arrays, amortizing Python dispatch over entire batches. The GTO-to-Lunar benchmark, by contrast, invokes user-defined Python code at every integration step- work that cannot be batched.

## Analysis

The two benchmarks bound an important design decision: the gap between Go and Python narrows significantly when Python delegates inner-loop work to compiled NumPy or SciPy extensions, and widens dramatically when the inner loop must call user-defined Python functions. For mission-planning tools and parameter sweeps where integration rate functions are authored by the user, Go's 200× advantage translates directly into search space expansion: a parameter sweep that previously required a week of compute time fits in hours, enabling more complex mission scenarios. For geometry or linear-algebra intensive pipelines where NumPy batching is practical, the improvement is real but smaller.

# Embedded Hardware

## TinyGo

TinyGo is a Go compiler targeting microcontrollers (MCUs), WebAssembly, and conventional desktop operating systems (Linux, Windows, macOS). It combines the LLVM compiler infrastructure with a modified Go runtime that eliminates features incompatible with severely resource-constrained hardware: no dynamic linking, a minimal garbage collector, and aggressive dead-code elimination [@tinygo2025]. The result is binaries small enough for the flash and RAM budgets of MCUs. TinyGo supports 52 processor architectures across 160 development boards, including ARM Cortex-M families (STM32, nRF, SAMD, RP2040/RP2350) that appear in CubeSat on-board computers and payload controllers.

**Real-time behaviour.** A performance evaluation on an ESP32 [@torrez2023] found that C, Rust, and MicroPython all ran on FreeRTOS and all exhibited measurable execution-time jitter, while TinyGo ran without FreeRTOS and showed none.This distinction warrants care: TinyGo does include a goroutine scheduler and, functionally, provides most of what an MCU-class RTOS offers. The difference is one of scope and complexity- TinyGo's scheduler is cooperative, constrained, and purpose-built around Go's concurrency model, whereas FreeRTOS is a general-purpose preemptive kernel. The timing advantage likely reflects the lower overhead and determinism of TinyGo's simpler scheduler rather than the absence of scheduling altogether. The authors conclude that C/C++, TinyGo, and Rust are more suitable when execution and response time are key factors, while Python is appropriate only for less strict requirements [@torrez2023]. For closed-loop control or sensor sampling where phase-margin requirements must be met deterministically, this property is significant.

**Memory footprint.** A study on TinyJambu cryptographic primitives [@tinyjambu2023] reports a TinyGo binary of 19 kB versus C and Rust binaries exceeding 66 kB for equivalent functionality, a reduction of approximately 3.5×. Smaller binaries reduce flash requirements and can be decisive when selecting between MCU families for a given subsystem.

**Garbage collector and deterministic allocation.** TinyGo's conservative mark-and-sweep GC runs on constrained hardware but does not compact the heap, leaving long-running allocating programs vulnerable to exhaustion through fragmentation. With the GC disabled, the binary carries no runtime overhead. One can strip down the Go runtime with flags like `-gc=leaking -scheduler=none -panic=trap`. Mitigation strategies for GC non-determinism are discussed in the Allocation Discipline section.

**Concurrency model.** TinyGo provides a cooperative goroutine scheduler with the same API as standard Go: goroutines, channels, `sync.Mutex`. Teams can develop and test concurrent software on the desktop and target the MCU without rewriting synchronization logic to a C RTOS API. This is the core of the single-language-stack thesis: the same concurrency idioms (goroutines, channels, mutexes) that coordinate a desktop simulation run unmodified on the MCU target.

## TamaGo

TamaGo is a framework for compiling Go programs to bare-metal execution on application-class SoCs (System-on-Chip), without a RTOS, a C standard library, or a POSIX-like kernel layer [@barisani2025]. Its motivation was reducing attack surface in high-assurance embedded software by eliminating the implicit trust relationship with a complex operating system or runtime shim.

TamaGo consists of two components: a minimally patched Go distribution that enables bare-metal compilation, and a set of platform-support packages for hardware initialization, peripheral drivers, and interrupt handling. A TamaGo binary boots directly into the Go runtime; there is no separate bootloader unless one is explicitly included. The memory space is flat with no virtual memory abstraction. The `unsafe` package is used in exactly three locations (Register and DMA packages), and the entire peripheral driver layer is written in Go.

The binary size of TamaGo packages is notably compact: a True Random Number Generator driver is approximately 80 lines of code; a 10/100 Mbps Ethernet driver with MII support is approximately 400 lines; AMD64 MMU, SMP, exception, and IRQ handling total approximately 1000 lines. The patching required to the Go runtime to support this model amounts to approximately 3000 lines. This patch is feasible because the Go team deliberately avoided linking to libc and Go has comprehensive assembly support [@barisani2025].

Practically, a Go developer requires a single import of the target device package to enable the necessary hardware initializations. The build process is identical to standard Go. TamaGo also provides `armory-boot`, a primary signed bootloader in 700 lines of Go, and `go-boot`, a UEFI shell and OS loader for AMD64 in approximately 2000 lines. Without networking the EFI image is $\approx 3$ MB; adding full TLS/SSH support and UEFI networking through SNP brings it to $\approx 11$ MB, reducible to $\approx 9$ MB by trimming the TLS certificate bundle and debug profiling. Equivalent functionality in C or C++ would require linking millions of lines of C and a POSIX kernel layer.

A particularly relevant property for aerospace applications is TamaGo's support for Trusted Execution Environment (TEE) unikernels, including lockstep execution: the same process runs in two concurrent hardware threads with identical deterministic inputs, and any divergence signals a fault. While designed for security against physical glitch injection, the same mechanism addresses single-event upset (SEU) concerns in radiation environments. Using the GoTEE library this configuration requires approximately 20 lines of Go [@gotee2024].

Networking across both TinyGo and TamaGo targets is being unified under `lneto`, a pure-Go userspace networking library with no OS dependencies [@lneto2025]. It implements Ethernet II, IPv4/IPv6, TCP, UDP, ARP, DHCP, DNS, and HTTP/1.1 with zero heap allocations per operation, making it suitable from RP2040-class MCUs up to bare-metal SoCs. A minimal TinyGo binary with `lneto` networking compiles to 185 kB.

TamaGo primarily targets application-class processors (ARM Cortex-A, AMD64). The experimental `kotama` branch extends this to RISC-V targets with as little as 6 MB of RAM (SiFive FU540), using soft floating-point and a reduced library footprint [@kotama2025]. Below that threshold, TinyGo remains the appropriate compiler; MCUs such as STM32 or RP2040 are outside both projects' scope.



# Fortran Transpilation

## Motivation and Pipeline

Heritage aerospace mathematical models such as aerodynamic databases, propulsion tables, orbit-determination algorithms or atmospheric models, are disproportionately implemented in Fortran. These models represent decades of validation effort and institutional knowledge. Rewriting them by hand or with the help of an AI agent in a modern language is expensive, and risks introducing new defects in the translation. Keeping them in Fortran creates a dependency on Fortran compilers, toolchains, and expertise that grows harder to maintain as those communities age.

A source-to-source transpiler offers a middle path: mechanical translation of a defined subset of Fortran 90 into idiomatic, testable Go modules that preserve the original mathematics without manual reinterpretation. The translated code is readable, can be integrated into Go test harnesses, and the translation process itself acts as a static analysis pass that enforces rules the Fortran compiler does not.

The transpiler enforces strict argument-count checking at every call site: it counts the formal parameters of each subroutine declaration and verifies that every call passes exactly that many arguments. Fortran's external linkage does not perform this check, as too few arguments read uninitialized stack memory, too many shift the effective argument mapping; and both are legal Fortran that compile without diagnostics. Rather than emit a silently incorrect translation, the transpiler refuses to proceed and returns a structured error identifying the source file, line number, subroutine name, and defect class.

## Case Study: NASA GEODYN-IIE

GEODYN-IIE is NASA Goddard Space Flight Center's operational software system for precision orbit determination and geodetic parameter estimation, written in Fortran over several decades [@rowlands1993]. The system is approximately 550 000 lines of Fortran source. Transpiling, fixing, and documenting defects in a representative subset (`g2e.f90`) produced a diff of +234 / -108 lines across 8 defect categories.

**Category 1 - Missing arguments (15 call sites).** Subroutine signatures had evolved over time where arguments were added to handle new capabilities but call sites throughout the large multi-file codebase were not updated. Two examples: `ACCSEL` calls `ORBSET` without the `KNSTEPS` orbit step count, so position integration runs with a garbage value from uninitialized stack memory. The VLBI delay subroutine `ERM_NA` is called without the `RC2Keps` and `RC2Kpsi` output arrays, leaving Earth rotation partial derivative matrices unfilled and nutation partials corrupt.

**Category 2 - Extra arguments (5 call sites).** Arguments were removed from subroutine signatures but some call sites continued passing the old argument, shifting the effective parameter mapping by one position. In `VLBI` delay processing, a spurious `ACCL_GEOM` argument shifted all subsequent arguments, causing the rotation-matrix multiplication to receive wrong inputs.

**Category 3 - Stack corruption (2 sites).** A scalar was supplied where an array was expected, causing the called subroutine to read adjacent stack memory as array elements. In troposphere delay processing, `TROP_HZD` was used as a stand-in for the two-element array `LONG(2)`, producing incorrect VMF1 hydrostatic mapping coefficients.

**Category 4 - Typos causing silent incorrect results (6 instances).** Single-character substitutions that compile without error but produce wrong numerical output: the letter `O` for the digit `0` in a variable name (`ZE2O` instead of `ZERO`) caused an observation-count branch to read an uninitialized variable and never trigger; a quaternion flag typo (`LDVECT` vs. `LDVCT`) caused satellite attitude to always be treated as absent; a solar eclipse typo (`beta0` vs. `BETA`) caused NaN to propagate into attitude calculations. When `|BETA| < 1e-6`, a guard clamped `COSEPSILON` to ±1. The next line computes `SINEPSILON = SQRT(1 - COSEPSILON²)`; a super-unity `COSEPSILON` makes the argument negative, `sqrt` of a negative value produces quiet NaN (IEEE754). The typo replaced `BETA` with the uninitialized `beta0`, so the guard could fail to engage causing a NaN propagation through all downstream attitude calculations.

**Category 5 - Control-flow defects.** Uninitialized variables in conditional branches produced non-deterministic behavior: `LNELEV` was used in `IF(LNELEV) GO TO 1000` before any assignment, causing an arbitrary branch at startup; `MEMMSS` and `IOS` were checked in `ALLOCATE` status clauses without prior initialization, so allocation-failure guards could fire spuriously. The `ENTRY`-based shared procedure bodies `DWRITE`/`DREAD` were restructured into separate subroutines, as `ENTRY` has no Go equivalent.

**Category 6 - Hardcoded indices.** VLBI delay correction link pointers `JDLCTK` and `JDLCTI` were set to the literal constant `1`. All other `JDLCT*` variables in the same block were runtime-derived from `KDELCT`. The hardcoded value produced correct results only for single-arc, single-satellite runs; multi-arc solutions applied the wrong delay correction.

**Category 7 - Missing COMMON block.** The variance-matrix filter flags `LVMTF` and `LVMTFO` were absent from a subroutine that conditioned processing on them. Without the `/VMATFL/` declaration, Fortran's implicit typing rule (`LOGICAL(L)`) creates local variables of the same names that are entirely disconnected from the global COMMON block and carry undefined values. Referencing an undefined variable is undefined behavior under the Fortran standard (ISO/IEC 1539:1991, §14.7.5; ANSI X3.9-1978, §16.1).

**Category 8 - Missing output matrix declarations.** Earth rotation partial derivative output arrays in `ERM_NA` were absent from the calling subroutine's declaration section, so outputs went into undefined memory and nutation partials were incorrect.

## Value Proposition

All defects above are legal Fortran; none were caught by `gfortran`, `ifort`, or `ftnchek`. Whole-program cross-file analysis is beyond what existing Fortran tooling performs. A complete successful translation is therefore a certificate of argument-count and declared-type correctness across the translated subset; and the resulting Go code is immediately testable against known-correct numerical outputs.


# Flight Dynamics Toolkit: gnco

`gnco` [@gnco2025] is an open-source Go library providing building blocks for 3-to-6-DoF flight dynamics simulation: coordinate frame transformations (body, velocity, geographic, inertial), WGS84 geodesy with J2 gravity, ISA 1976 atmosphere, aerodynamic force models, a nozzle thrust model, and an analytical Keplerian orbit package (`orbits`) that computes position, velocity, anomalies, angular momentum, specific energy, and period directly from orbital elements, implementing the classical two-body solutions of Curtis [@curtis2013]. The library is applied in the `examples/5dof-rocket` program, which assembles these components into a 5-DoF sounding rocket simulation covering a single-stage vehicle from launch through apogee; validated against TRAEC software, a reference trajectory analysis tool created by Instituto de Investigaciones Aeronauticas y Espaciales, it predicts an apogee of approximately 45 km for a 1800 kg, 40 kN vehicle at 85° elevation, with agreement within 0.5%.

## RKN12(10) Integrator

The central technical contribution of `gnco` is its numerical integrator. Most trajectory codes apply a general-purpose ODE solver (i.e Runge-Kutta 4 or Dormand-Prince 5/4) to the augmented first-order state $(x, v)$, even though the equations of motion are second-order: $\ddot{x} = f(t, x)$ with no explicit dependence on $\dot{x}$ during unpowered flight. The Runge-Kutta-Nyström (RKN) family operates directly on second-order ODEs, avoiding this augmentation. The RKN12(10) variant [@prince1987] uses 17 function evaluations per step to achieve 12th-order accuracy in position, with an embedded 10th-order solution for adaptive step-size control.

For unpowered orbital arcs the integrator is nearly energy-conserving over arbitrarily long windows. The `examples/keplerian-orbit` program quantifies this by propagating a LEO two-body orbit (400 km perigee, 500 km apogee, $e = 0.007$, $T = 5607$ s) for 5 complete revolutions at a fixed step of 300 s, corresponding to only 18.7 steps per orbit, and measuring the maximum relative specific energy error $|\Delta E / E_0|$.

The measured error is approximately 60 times double-precision machine epsilon ($\epsilon_m \approx 2.2 \times 10^{-16}$), preserving orbital energy to within two orders of magnitude of floating-point representational limits over five full revolutions at fewer than 19 steps per orbit.


# Engineering Practices and Limitations

## Allocation Discipline

Go's garbage collector introduces latency non-determinism proportional to allocation rate: the more memory a program allocates per unit time, the more frequently the GC runs, and the more CPU cycles it consumes. For aerospace applications with throughput or latency constraints, controlling allocation rate is the primary engineering lever.

TinyGo's escape analysis tooling makes every heap allocation visible at compile time via the `-print-allocs` flag. Engineers can inspect the output, identify allocating sites, and restructure the code, typically by passing pointers explicitly rather than returning values until the inner loop is allocation-free. The compiler directive `//go:noheap` enforces this mechanically: any function so annotated that allocates produces a compile-time error, turning an auditing concern into a build constraint.

The two runtime parameters that control GC behaviour without recompilation are `GOGC` (the ratio of new allocation to live heap that triggers a collection; default 100) and `GOMEMLIMIT` (a soft upper bound on total heap size that causes the GC to collect more aggressively as the limit is approached). Together they allow operators to tune GC aggressiveness independently of the compiled binary. These parameters are not yet available in TinyGo.

## Known Limitations

Go is not appropriate for all aerospace applications today. Three gaps are material:

**No DO-178C qualification toolchain.** Avionics software for certified aircraft must be developed under a DO-178C process that includes traceability from requirements to source to object code and verification of the compiler itself. No DO-178C-qualified Go compiler currently exists. TinyGo and standard Go are appropriate for research spacecraft, university CubeSats, ground support equipment, and mission operations software, but not for certified flight software on crewed or safety-critical applications without additional toolchain qualification work.

**Thin scientific library ecosystem.** Python's dominance in scientific computing has produced a deep ecosystem of validated numerical libraries. Go's equivalents, such as `gonum`, scientific SDF libraries, and orbital mechanics packages, are growing but remain neither as broad nor as deeply validated. Teams starting new numerical projects may find themselves implementing algorithms that already exist in Python.

**Interface heap escapes.** Calling a method through an interface causes the compiler to conservatively mark receiver arguments as heap-escaping when the underlying type is unknown at compile time. This is a practical obstacle for allocation-free HAL abstractions (SPI, I2C drivers): the interface boundary undermines the allocation discipline achieved in the concrete implementation. Extending `//go:noheap` to cover interface values is tracked in TinyGo Github issue #3809.

## Operational Use

`golaborate` [@golaborate] is an open-source Go library from NASA JPL providing HTTP-based instrument control for laboratory hardware, with drivers for cameras, motion controllers, and test equipment. It is used across several NASA/JPL programmes including Roman-CGI, PIAACMC, EMIT, and the Decadal Survey Testbed. Client libraries for the server are roughly one-tenth its line count, with no external dependencies and cross-platform static binaries. These are properties that lower integration friction across heterogeneous ground-system environments.

The first author was informed by a JPL/Caltech engineer that `golaborate` and `pctl` [@pctl] (a high-performance discrete control library) power the wavefront sensing and control loop on the Nancy Grace Roman Space Telescope Coronagraph Instrument, operating at 500 Hz [@shields2024] with GC pauses peaking at ~400us and loop body of ~120us- placing standard Go, with its concurrent garbage collector, in continuous quasi-real-time service on an active NASA instrument.

# Conclusions

We have presented four practical contributions establishing Go as a viable language for aerospace software development across the desktop-to-embedded continuum.

The GTO-to-Lunar trajectory benchmark demonstrates that Go achieves up to 200× speedup over NumPy-based Python for user-authored integration kernels, expanding the viable search space for mission planning and parameter sweeps from weeks to hours. The SDF benchmark confirms that the improvement narrows to approximately 4× when Python delegates inner-loop work to compiled NumPy extensions. This provides engineers with a concrete model for estimating where Go's performance advantage is material.

TinyGo and TamaGo address the embedded tier. TinyGo produces jitter-free, allocation-auditable binaries for ARM Cortex-M microcontrollers that are competitive with C in timing stability; in its GC-free mode it achieves a smaller binary than C with libc. TamaGo enables bare-metal SoC execution with full Go networking, cryptography, and optional lockstep SEU protection, in 3 MB, without a RTOS or C-shim layer.

The Fortran transpiler demonstrates that source-to-source migration from heritage Fortran to testable Go modules is feasible and that the translation process itself constitutes a whole-program static analysis pass. Application to NASA GEODYN-IIE surfaced several categories of latent defect across 25+ call sites that had been invisible to Fortran compilers for decades.

`gnco` demonstrates that Go can host numerically demanding flight dynamics without complex numerical libraries. Its RKN12(10) integrator exploits the second-order structure of the equations of motion to achieve near-machine-precision energy conservation at 300 s step sizes.

The gaps are real: no DO-178C qualification toolchain exists for Go, and the scientific library ecosystem lags behind Python. For lean teams developing research spacecraft, CubeSats, simulation tools, or mission operations software, however, Go offers a pragmatic middle path: the development speed of a high-level language, the runtime performance of a compiled language, and a single unified stack from ground to flight.

# Disclosure

The authors declare no conflicts of interest.

*This document was prepared in Markdown and converted to \LaTeX using the open-source [github.com/soypat/goldmark-latex](https://github.com/soypat/goldmark-latex) `md2latex` tool.*

<!-- Bibliography rendered from iaa.bib -->
