using System;
using System.IO;
using System.Linq;
using EXM.MatricPro.Actions;
using EXM.MatricPro.Util;

/// <summary>Checks that an offline-generated starter deck survives MATRIC's real import and export code.</summary>
internal static class VerifyNativeImport {
    /// <summary>Imports into caller-owned isolated collections and verifies native configuration and bundled resources.</summary>
    private static void Main(string[] args) {
        string package = Path.GetFullPath(args[0]);
        string root = Path.GetFullPath(args[1]);
        string first = Path.Combine(root, "first");
        var imported = DeckImporter.ImportDeck(package, first);
        if (!imported.Success) throw new InvalidDataException(imported.ErrorMessage);
        var deck = imported.ImportedDeck;
        if (deck.Pages.Count != 2 || deck.Pages.Sum(p => p.Controls.Count) != 5) throw new InvalidDataException("Unexpected starter layout.");
        var copy = deck.Pages[0].Controls[0].ControlEvents[0].Actions[0] as ActionHotkeyConfig;
        if (copy == null || copy.KeyCode != 67 || !copy.Modifiers.Contains("LCONTROL")) throw new InvalidDataException("Hotkey configuration was lost.");
        string image = Path.Combine(first, deck.Id, "panel.svg");
        byte[] expectedImage = File.ReadAllBytes(image);
        string exported = DeckResourceHelper.ExportDeck(deck.Id, false, first, Path.Combine(root, "exports"));
        var second = DeckImporter.ImportDeck(exported, Path.Combine(root, "second"));
        if (!second.Success) throw new InvalidDataException(second.ErrorMessage);
        if (!expectedImage.SequenceEqual(File.ReadAllBytes(Path.Combine(root, "second", deck.Id, "panel.svg")))) throw new InvalidDataException("Bundled image changed.");
        if (second.ImportedDeck.Pages.Sum(p => p.Controls.Count) != 5) throw new InvalidDataException("Round-trip changed the control count.");
        Console.WriteLine("PASS: native import/export/reimport; 2 pages, 5 controls, hotkey configuration and SVG resource preserved. No actions executed.");
    }
}
