import time

from app.dependencies.extractor import DependencyExtractor


def benchmark():
    extractor = DependencyExtractor()

    for line_count in (10_000, 50_000, 100_000):
        source_code = "\n".join(
            f"value_{i} = helper_{i}()"
            for i in range(line_count)
        )

        start = time.perf_counter()

        dependencies = extractor.extract(
            source_code,
            "benchmark.py",
            "python",
        )

        elapsed = time.perf_counter() - start

        print(
            f"Lines: {line_count:,} | "
            f"Dependencies: {len(dependencies):,} | "
            f"Time: {elapsed:.2f} seconds"
        )


if __name__ == "__main__":
    benchmark()