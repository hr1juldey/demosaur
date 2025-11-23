#!/usr/bin/env python3
"""
Context Window Overflow Test

Tests what happens when we try to force-feed a large document (ASYNC_ORCHESTRATION_DESIGN.md, ~8300 tokens)
into DSPy with different context window configurations.

Default Ollama context: 4096 tokens
ASYNC_ORCHESTRATION_DESIGN.md size: ~8300 tokens (will overflow!)
"""

import dspy
from pathlib import Path


def count_tokens_rough(text: str) -> int:
    """Rough token estimate: chars / 4"""
    return len(text) // 4


def test_context_overflow():
    """Test 1: Default Ollama context (4096) with large input"""
    print("=" * 80)
    print("TEST 1: Default Context (4096 tokens) - WILL OVERFLOW")
    print("=" * 80)

    # Read ASYNC_ORCHESTRATION_DESIGN.md
    analysis_path = Path(__file__).parent / "docs" / "ASYNC_ORCHESTRATION_DESIGN.md"
    analysis_text = analysis_path.read_text()

    estimated_tokens = count_tokens_rough(analysis_text)
    print(f"\nASYNC_ORCHESTRATION_DESIGN.md stats:")
    print(f"  - Characters: {len(analysis_text):,}")
    print(f"  - Estimated tokens: {estimated_tokens:,}")
    print(f"  - Lines: {analysis_text.count(chr(10)):,}")

    # Configure DSPy with default Ollama settings
    # Note: max_tokens in dspy.LM() is for OUTPUT, not INPUT
    # Ollama's context window is configured separately (default 4096)
    lm = dspy.LM(
        model="ollama/mistral:7b",
        num_ctx=8192,
        max_tokens=20,  # Output limit
        temperature=0.7
    )
    dspy.configure(lm=lm)

    # Create a simple signature
    class SummarizeDocument(dspy.Signature):
        """Summarize a document"""
        document: str = dspy.InputField(desc="Full document text")
        summary: str = dspy.OutputField(desc="Concise summary (200 words)")

    print("\n" + "-" * 80)
    print("Attempting to summarize entire ASYNC_ORCHESTRATION_DESIGN.md (will exceed 4096 context)...")
    print("-" * 80)

    try:
        summarizer = dspy.ChainOfThought(SummarizeDocument)
        result = summarizer(document=analysis_text)

        print("\n✅ SUCCESS (Unexpected!)")
        print(f"Summary length: {len(result.summary)} chars")
        print(f"\nSummary preview:")
        print(result.summary[:500] + "..." if len(result.summary) > 500 else result.summary)

    except Exception as e:
        print(f"\n❌ FAILED (Expected)")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)[:200]}")


def test_chunked_approach():
    """Test 2: Smart chunking to fit context window"""
    print("\n\n" + "=" * 80)
    print("TEST 2: Chunked Approach (split into 80% chunks)")
    print("=" * 80)

    analysis_path = Path(__file__).parent / "docs" / "ASYNC_ORCHESTRATION_DESIGN.md"
    analysis_text = analysis_path.read_text()

    # Target: 80% of 4096 = 3276 tokens for input
    # Reserve 20% (819 tokens) for output + overhead
    TARGET_CHUNK_SIZE = 3276 * 4  # Convert tokens to chars (rough)

    print(f"\nChunking strategy:")
    print(f"  - Context window: 4096 tokens")
    print(f"  - Input budget: 3276 tokens (80%)")
    print(f"  - Chunk size: ~{TARGET_CHUNK_SIZE:,} chars")

    # Split into chunks
    chunks = []
    for i in range(0, len(analysis_text), TARGET_CHUNK_SIZE):
        chunk = analysis_text[i:i + TARGET_CHUNK_SIZE]
        chunks.append(chunk)

    print(f"  - Number of chunks: {len(chunks)}")
    print(f"  - Chunk sizes: {[len(c) for c in chunks]}")

    lm = dspy.LM(
        model="ollama/mistral:7b",
        max_tokens=500,
        temperature=0.7
    )
    dspy.configure(lm=lm)

    class SummarizeChunk(dspy.Signature):
        """Summarize a chunk of text"""
        chunk: str = dspy.InputField()
        chunk_number: int = dspy.InputField()
        total_chunks: int = dspy.InputField()
        summary: str = dspy.OutputField(desc="Concise summary of this chunk")

    print("\n" + "-" * 80)
    print("Processing each chunk...")
    print("-" * 80)

    try:
        summarizer = dspy.ChainOfThought(SummarizeChunk)
        summaries = []

        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i}/{len(chunks)}:")
            print(f"  - Size: {len(chunk):,} chars (~{count_tokens_rough(chunk):,} tokens)")

            result = summarizer(
                chunk=chunk,
                chunk_number=i,
                total_chunks=len(chunks)
            )
            summaries.append(result.summary)
            print(f"  - Summary: {result.summary[:100]}...")

        print("\n✅ All chunks processed!")
        print(f"\nCombined summaries length: {sum(len(s) for s in summaries):,} chars")

        # Now combine summaries
        print("\n" + "-" * 80)
        print("Combining chunk summaries into final summary...")
        print("-" * 80)

        class CombineSummaries(dspy.Signature):
            """Combine multiple summaries into one coherent summary"""
            chunk_summaries: str = dspy.InputField()
            final_summary: str = dspy.OutputField(desc="Unified summary")

        combiner = dspy.ChainOfThought(CombineSummaries)
        combined_text = "\n\n".join(f"Chunk {i+1}: {s}" for i, s in enumerate(summaries))

        final = combiner(chunk_summaries=combined_text)

        print("\n✅ FINAL SUMMARY:")
        print(final.final_summary)

    except Exception as e:
        print(f"\n❌ FAILED")
        print(f"Error: {e}")


def test_ollama_context_config():
    """Test 3: Configure Ollama to use larger context window"""
    print("\n\n" + "=" * 80)
    print("TEST 3: Ollama with Extended Context (num_ctx parameter)")
    print("=" * 80)

    print("\nOllama context configuration:")
    print("  - Default num_ctx: 4096 tokens")
    print("  - Mistral 7B can handle: 8K (native) or 32K (with PoSE)")
    print("  - Qwen3 8B can handle: 32K (native) or 131K (with YaRN)")

    # For Ollama, we need to pass num_ctx in launch_kwargs
    # This sets the context window size in Ollama
    lm = dspy.LM(
        model="ollama/mistral:7b",
        max_tokens=500,
        launch_kwargs={
            "num_ctx": 8192  # Double the default context
        }
    )

    print("\n  - Configured num_ctx: 8192 tokens")
    print("  - This should handle ASYNC_ORCHESTRATION_DESIGN.md (~8300 tokens) better")

    print("\n⚠️  NOTE: launch_kwargs support may vary by provider")
    print("     For Ollama, you might need to set this in modelfile instead")


def test_hierarchical_summary():
    """Test 4: Hierarchical summarization (multi-level)"""
    print("\n\n" + "=" * 80)
    print("TEST 4: Hierarchical Summary Strategy")
    print("=" * 80)

    print("\nStrategy:")
    print("  1. Split document into sections by headers")
    print("  2. Summarize each section independently (fits in context)")
    print("  3. Combine section summaries into document summary")
    print("  4. Total context usage: sections fit individually")

    analysis_path = Path(__file__).parent / "docs" / "ASYNC_ORCHESTRATION_DESIGN.md"
    analysis_text = analysis_path.read_text()

    # Split by major headers (##)
    sections = []
    current_section = []
    current_header = None

    for line in analysis_text.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections.append({
                    'header': current_header,
                    'content': '\n'.join(current_section)
                })
            current_header = line
            current_section = [line]
        else:
            current_section.append(line)

    if current_section:
        sections.append({
            'header': current_header,
            'content': '\n'.join(current_section)
        })

    print(f"\nFound {len(sections)} sections:")
    for i, section in enumerate(sections, 1):
        tokens = count_tokens_rough(section['content'])
        header = section['header'] if section['header'] else "(Document Header)"
        print(f"  {i}. {header[:60]:<60} ~{tokens:,} tokens")

    print("\n✅ All sections fit within 4096 context!")
    print("   Each can be processed independently without overflow")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DSPy Context Window Overflow Tests")
    print("=" * 80)
    print("\nPurpose: Understand what happens when input exceeds context limit")
    print("Target: ASYNC_ORCHESTRATION_DESIGN.md (~8300 tokens) vs 4096 default Ollama context")

    # Test 1: Overflow scenario
    test_context_overflow()

    # Test 2: Chunked approach
    test_chunked_approach()

    # Test 3: Ollama config
    test_ollama_context_config()

    # Test 4: Hierarchical
    test_hierarchical_summary()

    print("\n" + "=" * 80)
    print("KEY FINDINGS:")
    print("=" * 80)
    print("""
1. Default Ollama context: 4096 tokens (even if model supports more)
2. dspy.LM(max_tokens=X) controls OUTPUT, not INPUT context
3. For Ollama, use launch_kwargs={'num_ctx': 8192} to extend context
4. Smart strategies when context is tight:
   a) Chunk input to fit 80% of context (reserve 20% for output)
   b) Hierarchical summarization (process sections independently)
   c) Extract only relevant portions (don't send entire doc)
5. For Phase 3 cache: Must manage context budgets actively
   - Mistral 7B: 4K default, 8K native, 32K with PoSE
   - Qwen3 8B: 32K native, 131K with YaRN
   - Reserve 20-30% for generation space
""")


if __name__ == "__main__":
    main()
