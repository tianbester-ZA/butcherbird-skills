# Making a scene in Higgsfield

Use the client's own photography first. Generate only when the scene you need doesn't exist: the product somewhere it has never been photographed. Generation makes the picture around the real product; it doesn't invent the brand's look.

Higgsfield is connected to Claude as an MCP server (a plug-in that gives Claude its tools). It costs credits: say roughly how many before starting. One image at 2k on Nano Banana Pro has cost about 2 credits (16 Nov 2026); check the cost with `get_cost: true` first.

## What to ask for
- **The real product as the reference.** Upload the client's packshots and pass them as reference images, so the model draws the right shape and colours.
- **Front-on, labels uncovered.** Eye level, straight on, nothing across the label (no ribbon, hand or prop). You'll lay the real label over it later (`labels.md`), and that only works on a pack facing you.
- **The top 45% empty.** A quiet wall, sky, curtain or dark. That's where the type goes.
- **Real light.** A contact shadow under the product, light from one direction, matching the scene.
- **9:16.** It returns 1536 x 2752. Make the 9:16 scene; the 4:5 and 1:1 reuse it, moved.

Example prompt, for the invented Fynn brand:

> The sock box from the reference image standing on a stone hearth in a wooden cabin at night, fire glowing to the right, front face straight to camera at eye level, label fully visible and uncovered, soft contact shadow, warm firelight from the right. The top half of the frame is a plain dark timber wall with nothing on it. Photographic, natural colour, no text added.

## How Claude does it (the tool steps)
1. `media_upload` with the packshot's filename. It returns an upload address.
2. Send the file there with curl, a PUT with `Content-Type` set (e.g. `image/png`) and the header `If-None-Match: *`.
3. `media_confirm` to finish the upload. It gives a media id.
4. `models_explore` once, to see the model's reference role name and aspect ratios.
5. `generate_image_batch` with model `nano_banana_pro`, `aspect_ratio: "9:16"`, the prompt, and `medias: [{ value: <media id>, role: <reference role> }]`. One request per scene; up to 12 at once.
6. `jobs_wait` until they finish, then download the results into the job folder (`scenes/`), never into the skill.

## Then
Look at every result at full size. Pick with the person. Expect the label to be wrong: that's normal and step 4 fixes it. If the product is tilted, covered or turned away, regenerate rather than fight it.
