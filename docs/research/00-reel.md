# The reel this project starts from

- **Source:** https://www.instagram.com/reel/DeKWvd1BAX-/
- **Author:** graphicule.dev (James, now Etchpad, etchpad.ai), posted 2026-10-06
- **Caption:** "Code is hard to read, can a better layout make it faster and easier to understand? If we parse code into blocks, and rearrange the blocks semantically, does this make a storyline that's easier for a human to digest?"

The reel and its example code are the author's. This page only summarises them. [examples/library-ts](../../examples/library-ts) is our own file with the same shape: types at the top, a class, then functions with the entry point last.

## What the reel shows

| Time | What happens |
|---|---|
| 0:00–0:30 | A flat TypeScript file with an order status type, three interfaces, an inventory class and three functions, the entry point last. He traces it top to bottom and circles every name you have to hold in your head. |
| 0:32–0:37 | Each declaration gets a box. The class box holds one box per method and one for the constructor. |
| 0:37–0:47 | The boxes are pulled apart on a dark canvas, and the class becomes a container. |
| 0:50–1:30 | "Code storyline", read left to right: the entry point, then the two functions it calls, then the class (its methods in call order), then the data structures. |
| 1:32 | Zoomed out, the whole file reads as one left-to-right story. |

## What we took from it

1. **The file and the storyline run in opposite orders.** The file is written bottom-up, types first and entry point last. The storyline is read top-down, entry point first and data last.
2. **Boxes hold the real code, unchanged.** The only added text is a two- or three-word label, such as "Entry point".
3. **Boxes split at declaration boundaries,** never in the middle of a function.
4. **A class is a frame around its methods,** and the methods inside it are in call order too.
5. **Arrows mean "calls" or "uses this type".** Nothing else.

## Where the reel goes wrong

At about 1:08 the canvas draws an arrow from the class to a data type the class never touches. Even on a 60-line file, arrows drawn by eye go wrong. That is why the skill's script refuses any arrow whose target is not named in the source block.

## What changed after research

- **Types:** the reel puts every type in a final column. Research on review order favours putting each type next to its first use (see [README.md](README.md)). After comparing both on a FastAPI example, the reel's column became the default ("column"), and the other layout became an option ("beside").
