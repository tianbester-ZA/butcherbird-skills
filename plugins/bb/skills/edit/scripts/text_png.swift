// text_png.swift: renders text overlays to transparent PNGs with CoreText.
// Why: Homebrew ffmpeg has no drawtext (no freetype), and Pillow is not
// in the system Python. CoreText ships with macOS, so this needs nothing installed.
// cut.py compiles it once to the pack's data folder and calls it with a JSON file:
//   [{"out": "a.png", "text": "WORDS HERE", "font": "/path/Geist-Black.ttf", "size": 72,
//     "color": "#FFFFFF", "accent": ["HERE"], "accent_color": "#EE7631",
//     "stroke": 0, "stroke_color": "#000000", "shadow": [0, 4], "shadow_color": "#000000B3",
//     "plate": null, "pad": 16, "leading": 0.9, "tracking": -0.01, "max_width": 940}]
// Prints [{"out": ..., "w": ..., "h": ...}] so cut.py can place and check the boxes.
import Foundation
import CoreText
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

func hexColor(_ s: String) -> CGColor {
    var h = s.trimmingCharacters(in: .whitespaces)
    if h.hasPrefix("#") { h.removeFirst() }
    var v: UInt64 = 0
    Scanner(string: h).scanHexInt64(&v)
    if h.count == 8 {
        return CGColor(srgbRed: CGFloat((v >> 24) & 0xff) / 255, green: CGFloat((v >> 16) & 0xff) / 255,
                       blue: CGFloat((v >> 8) & 0xff) / 255, alpha: CGFloat(v & 0xff) / 255)
    }
    return CGColor(srgbRed: CGFloat((v >> 16) & 0xff) / 255, green: CGFloat((v >> 8) & 0xff) / 255,
                   blue: CGFloat(v & 0xff) / 255, alpha: 1)
}

func loadFont(_ path: String, _ size: CGFloat) -> CTFont {
    let url = URL(fileURLWithPath: path) as CFURL
    if let descs = CTFontManagerCreateFontDescriptorsFromURL(url) as? [CTFontDescriptor], let d = descs.first {
        return CTFontCreateWithFontDescriptor(d, size, nil)
    }
    FileHandle.standardError.write("font not found: \(path), using Helvetica Neue Bold\n".data(using: .utf8)!)
    return CTFontCreateWithName("HelveticaNeue-Bold" as CFString, size, nil)
}

func norm(_ w: String) -> String {
    return w.uppercased().trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
}

let args = CommandLine.arguments
guard args.count > 1, let data = FileManager.default.contents(atPath: args[1]),
      let specs = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
    FileHandle.standardError.write("usage: text_png specs.json\n".data(using: .utf8)!)
    exit(2)
}

var results: [[String: Any]] = []
for spec in specs {
    let out = spec["out"] as! String
    let text = spec["text"] as? String ?? ""
    let size = CGFloat((spec["size"] as? NSNumber)?.doubleValue ?? 72)
    let font = loadFont(spec["font"] as? String ?? "", size)
    let color = hexColor(spec["color"] as? String ?? "#FFFFFF")
    let accentColor = hexColor(spec["accent_color"] as? String ?? "#EE7631")
    let accents = Set((spec["accent"] as? [String] ?? []).map(norm))
    let strokePct = CGFloat((spec["stroke"] as? NSNumber)?.doubleValue ?? 0)
    let strokeColor = hexColor(spec["stroke_color"] as? String ?? "#000000")
    let shadow = (spec["shadow"] as? [NSNumber])?.map { CGFloat($0.doubleValue) }
    let shadowColor = hexColor(spec["shadow_color"] as? String ?? "#000000B3")
    let plate = spec["plate"] as? String
    let pad = CGFloat((spec["pad"] as? NSNumber)?.doubleValue ?? 16)
    let leading = CGFloat((spec["leading"] as? NSNumber)?.doubleValue ?? 0.95)
    let tracking = CGFloat((spec["tracking"] as? NSNumber)?.doubleValue ?? 0)
    let maxW = CGFloat((spec["max_width"] as? NSNumber)?.doubleValue ?? 940)

    func attr(_ s: String, _ c: CGColor) -> NSAttributedString {
        var a: [NSAttributedString.Key: Any] = [
            NSAttributedString.Key(kCTFontAttributeName as String): font,
            NSAttributedString.Key(kCTForegroundColorAttributeName as String): c,
            NSAttributedString.Key(kCTKernAttributeName as String): size * tracking,
        ]
        if strokePct > 0 {
            a[NSAttributedString.Key(kCTStrokeWidthAttributeName as String)] = -strokePct
            a[NSAttributedString.Key(kCTStrokeColorAttributeName as String)] = strokeColor
        }
        return NSAttributedString(string: s, attributes: a)
    }
    func makeLine(_ words: [String]) -> CTLine {
        let m = NSMutableAttributedString()
        for (i, w) in words.enumerated() {
            if i > 0 { m.append(attr(" ", color)) }
            m.append(attr(w, accents.contains(norm(w)) ? accentColor : color))
        }
        return CTLineCreateWithAttributedString(m)
    }
    func width(_ l: CTLine) -> CGFloat { return CGFloat(CTLineGetTypographicBounds(l, nil, nil, nil)) }

    // Greedy wrap; an explicit "\n" in the text forces a break.
    var lines: [CTLine] = []
    for para in text.components(separatedBy: "\n") {
        var cur: [String] = []
        for w in para.split(separator: " ").map(String.init) {
            let trial = cur + [w]
            if !cur.isEmpty && width(makeLine(trial)) > maxW {
                lines.append(makeLine(cur)); cur = [w]
            } else { cur = trial }
        }
        if !cur.isEmpty { lines.append(makeLine(cur)) }
    }
    let asc = CTFontGetAscent(font), desc = CTFontGetDescent(font)
    let lineH = size * leading
    let textW = lines.map(width).max() ?? 0
    let textH = asc + desc + CGFloat(max(lines.count - 1, 0)) * lineH
    let sx = abs(shadow?[0] ?? 0), sy = abs(shadow?[1] ?? 0)
    let strokePx = size * strokePct / 100
    let W = Int(ceil(textW + 2 * pad + sx + 2 * strokePx)), H = Int(ceil(textH + 2 * pad + sy + 2 * strokePx))

    let cs = CGColorSpace(name: CGColorSpace.sRGB)!
    let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0, space: cs,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.setShouldAntialias(true)
    if let p = plate {
        ctx.setFillColor(hexColor(p))
        ctx.fill(CGRect(x: 0, y: sy, width: CGFloat(W) - sx, height: CGFloat(H) - sy))
    }
    let shadowBlur = CGFloat((spec["shadow_blur"] as? NSNumber)?.doubleValue ?? 0)
    if let s = shadow { ctx.setShadow(offset: CGSize(width: s[0], height: -s[1]), blur: shadowBlur, color: shadowColor) }
    for (i, l) in lines.enumerated() {
        let lw = width(l)
        let x = (CGFloat(W) - sx - lw) / 2
        let baselineFromTop = pad + strokePx + asc + CGFloat(i) * lineH
        ctx.textPosition = CGPoint(x: x, y: CGFloat(H) - baselineFromTop)
        CTLineDraw(l, ctx)
    }
    let img = ctx.makeImage()!
    let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: out) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, img, nil)
    CGImageDestinationFinalize(dest)
    results.append(["out": out, "w": W, "h": H, "lines": lines.count])
}
let o = try! JSONSerialization.data(withJSONObject: results)
print(String(data: o, encoding: .utf8)!)
