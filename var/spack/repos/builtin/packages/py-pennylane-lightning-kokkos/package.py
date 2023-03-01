# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)


from spack.package import *


class PyPennylaneLightningKokkos(CMakePackage, PythonExtension):
    """The PennyLane-Lightning-Kokkos plugin provides a fast state-vector simulator with Kokkos kernels."""

    homepage = "https://docs.pennylane.ai/projects/lightning-kokkos"
    git = "https://github.com/PennyLaneAI/pennylane-lightning-kokkos.git"
    url = (
        "https://github.com/PennyLaneAI/pennylane-lightning-kokkos/archive/refs/tags/v0.28.0.tar.gz"
    )
    tag = "v0.28.0"

    maintainers("vincentmr")

    version("main", branch="main")
    version("develop", commit="fd6feb9b2c961d6f8d93f31b6015b37e9aeac759")
    version("0.28.0", sha256="1d6f0ad9658e70cc6875e9df5710d1fa83a0ccbe21c5fc8daf4e76ab3ff59b73")

    backends = {
        "cuda": [False, "Whether to build CUDA backend"],
        "openmp": [False, "Whether to build OpenMP backend"],
        "openmptarget": [False, "Whether to build the OpenMPTarget backend"],
        "pthread": [False, "Whether to build Pthread backend"],
        "rocm": [False, "Whether to build HIP backend"],
        "serial": [True, "Whether to build serial backend"],
        # "sycl": [False, "Whether to build the SYCL backend"],
    }

    for backend in backends:
        deflt_bool, descr = backends[backend]
        variant(backend.lower(), default=deflt_bool, description=descr)
        depends_on(f"kokkos+{backend.lower()}", when=f"+{backend.lower()}", type=("run", "build"))

    variant(
        "build_type",
        default="Release",
        description="CMake build type",
        values=("Debug", "Release", "RelWithDebInfo", "MinSizeRel"),
    )
    variant("cppbenchmarks", default=False, description="Build CPP benchmark examples")
    variant("cpptests", default=False, description="Build CPP tests")
    variant("native", default=False, description="Build natively for given hardware")
    variant("sanitize", default=False, description="Build with address sanitization")
    variant("verbose", default=False, description="Build with full verbosity")

    extends("python")

    # hard dependencies
    depends_on("cmake@3.21:3.24,3.25.2:", type="build")
    depends_on("ninja", type=("run", "build"))
    depends_on("python@3.8:", type=("build", "run"))
    depends_on("py-setuptools", type="build")
    depends_on("py-pybind11", type=("build"))
    depends_on("py-pip", type=("build", "run"))
    depends_on("py-wheel", type="build")
    depends_on("py-pennylane", type=("run"))
    depends_on("py-pennylane-lightning~kokkos", type=("run"))

    # variant defined dependencies
    depends_on("llvm-openmp", when="+openmp %apple-clang")

    # Test deps
    depends_on("py-pytest", type=("test"))
    depends_on("py-pytest-mock", type=("test"))
    depends_on("py-flaky", type=("test"))


class CMakeBuilder(spack.build_systems.cmake.CMakeBuilder):
    build_directory = "build"

    def cmake_args(self):
        """
        Here we specify all variant options that can be dynamically specified at build time
        """
        args = [
            self.define_from_variant("CMAKE_BUILD_TYPE", "build_type"),
            self.define_from_variant("CMAKE_VERBOSE_MAKEFILE:BOOL", "verbose"),
            self.define_from_variant("PLKOKKOS_ENABLE_NATIVE", "native"),
            self.define_from_variant("PLKOKKOS_BUILD_TESTS", "cpptests"),
            self.define_from_variant("PLKOKKOS_ENABLE_SANITIZER", "sanitize"),
        ]
        args.append("-DCMAKE_PREFIX_PATH=" + self.spec["kokkos"].prefix)
        if "+rocm" in self.spec:
            args.append("-DCMAKE_CXX_COMPILER=" + self.spec["hip"].prefix.bin.hipcc)
        args.append(
            "-DPLKOKKOS_ENABLE_WARNINGS=OFF"
        )  # otherwise build might fail due to Kokkos::InitArguments deprecated
        return args

    def build(self, pkg, spec, prefix):
        super().build(pkg, spec, prefix)
        cm_args = ";".join([s[2:] for s in self.cmake_args()])
        args = ["-i", f"--define={cm_args}"]
        build_ext = Executable(f"{self.spec['python'].command.path} setup.py build_ext")
        build_ext(*args)

    def install(self, pkg, spec, prefix):
        pip_args = std_pip_args + [f"--prefix={prefix}", "."]
        pip(*pip_args)
        super().install(pkg, spec, prefix)

    @run_after("install")
    @on_package_attributes(run_tests=True)
    def install_test(self):
        pytest = which("pytest")
        pytest("tests")
        # with working_dir(self.stage.source_path):
        #     pl_runner = Executable(join_path(self.prefix, "bin", "pl-device-test"))
        #     pl_runner("--device", "lightning.kokkos", "--shots", "None", "--skip-ops")
