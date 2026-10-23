using System;
using System.IO;
using System.Linq;
using EXM.MatricPro;
using EXM.MatricPro.Actions;
using EXM.MatricPro.Controls.Config;
using EXM.MatricPro.Util;

/// <summary>Checks that offline-generated decks survives MATRIC's real import and export code.</summary>
internal static class VerifyNativeImport {
    /// <summary>Imports into caller-owned isolated collections and verifies native configuration and bundled resources.</summary>
    private static void Main(string[] args) {
        string package = Path.GetFullPath(args[0]);
        string root = Path.GetFullPath(args[1]);
        string first = Path.Combine(root, "first");
        var imported = DeckImporter.ImportDeck(package, first);
        if (!imported.Success) throw new InvalidDataException(imported.ErrorMessage);
        var deck = imported.ImportedDeck;
        bool dcs = args.Length > 2 && args[2] == "dcs";
        byte[] expectedImage = null;
        if (dcs) VerifyDcs(deck);
        else {
            if (deck.Pages.Count != 2 || deck.Pages.Sum(p => p.Controls.Count) != 5) throw new InvalidDataException("Unexpected starter layout.");
            var copy = deck.Pages[0].Controls[0].ControlEvents[0].Actions[0] as ActionHotkeyConfig;
            if (copy == null || copy.KeyCode != 67 || !copy.Modifiers.Contains("LCONTROL")) throw new InvalidDataException("Hotkey configuration was lost.");
            expectedImage = File.ReadAllBytes(Path.Combine(first, deck.Id, "panel.svg"));
        }
        string exported = DeckResourceHelper.ExportDeck(deck.Id, false, first, Path.Combine(root, "exports"));
        var second = DeckImporter.ImportDeck(exported, Path.Combine(root, "second"));
        if (!second.Success) throw new InvalidDataException(second.ErrorMessage);
        if (dcs) VerifyDcs(second.ImportedDeck);
        else {
            if (!expectedImage.SequenceEqual(File.ReadAllBytes(Path.Combine(root, "second", deck.Id, "panel.svg")))) throw new InvalidDataException("Bundled image changed.");
            if (second.ImportedDeck.Pages.Sum(p => p.Controls.Count) != 5) throw new InvalidDataException("Round-trip changed the control count.");
        }
        Console.WriteLine("PASS: native import/export/reimport (" + (dcs ? "DCS commands, mailbox and feedback bindings" : "starter hotkeys and SVG") + "). No actions executed.");
    }

    /// <summary>Checks DCS command configuration and feedback without starting the simulator or changing variables.</summary>
    private static void VerifyDcs(Deck deck) {
        if (deck.Pages.Count != 1 || deck.Pages[0].Controls.Count != 4) throw new InvalidDataException("Unexpected DCS example layout.");
        var actions = deck.Pages[0].Controls.SelectMany(c => c.ControlEvents).SelectMany(e => e.Actions).OfType<ActionSetServerVariableConfig>().ToList();
        if (actions.Count != 5 || actions.Any(a => a.VariableName != "DCS_INPUT_COMMAND")) throw new InvalidDataException("DCS command actions were lost.");
        if (actions[0].VariableValue.ToString() != "SYN_TEST_BUTTON 1" || actions[1].VariableValue.ToString() != "SYN_TEST_BUTTON 0") throw new InvalidDataException("Momentary press/release changed.");
        if (!actions.Any(a => (a.VariableCalculateValueFunction ?? "").Contains("eventData.value"))) throw new InvalidDataException("Scaled command calculation was lost.");
        var mailbox = deck.ReferencedUserVariables.Single(v => v.Name == "DCS_INPUT_COMMAND");
        if (mailbox.Value.ToString() != "" || mailbox.VariableType != MatricServerVariable.ServerVariableType.STRING) throw new InvalidDataException("Mailbox must stay empty.");
        var bindings = deck.Pages[0].Controls.SelectMany(c => ((MatricControlConfigBase)c.Config).ControlBindings).ToList();
        if (bindings.Count != 4 || !bindings.Any(b => b.PropertyPath == "state.value" && b.VariableName == "dcs_SYN_DIMMER")) throw new InvalidDataException("DCS feedback bindings were lost.");
    }
}
