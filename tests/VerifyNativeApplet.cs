using System;
using System.IO;
using System.Linq;
using System.Reflection;
using EXM.MatricPro.Controls.Config;
using EXM.MatricPro.Controls;
using EXM.MatricPro.Actions;
using EXM.MatricPro.Util;

/// <summary>Checks generated applet/deck packages against an explicitly supplied MATRIC build using isolated directories.</summary>
internal static class VerifyNativeApplet {
    /// <summary>Resolves only supplied build dependencies before entering native import code.</summary>
    private static int Main(string[] args) {
        AppDomain.CurrentDomain.AssemblyResolve += (sender, requested) => {
            string candidate = Path.Combine(args[0], new AssemblyName(requested.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        };
        try { Check(args); return 0; }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }

    /// <summary>Imports into a disposable Documents root and separate collections, then checks resources and native round-trip data.</summary>
    private static void Check(string[] args) {
        string root = Path.GetFullPath(args[3]);
        string documents = Path.Combine(root, "documents");
        Directory.CreateDirectory(documents);
        var constructor = typeof(AppletImporter).GetConstructor(BindingFlags.Instance | BindingFlags.NonPublic,
            null, new[] { typeof(string) }, null);
        if (constructor == null) throw new NotSupportedException("This build lacks an isolated Documents-root applet importer; do not use its real library.");
        var importer = (AppletImporter)constructor.Invoke(new object[] { documents });
        var applet = importer.ImportApplet(Path.GetFullPath(args[1]));
        if (!applet.Success) throw new InvalidDataException(applet.Message);
        string installed = Path.Combine(documents, "MATRIC", "custom", applet.Manifest.AppletId);
        foreach (string file in new[] { "manifest.json", "applet.html", "bridge.js", "history.js", "main.js", "style.css" })
            if (!File.Exists(Path.Combine(installed, file))) throw new InvalidDataException("Applet resource missing: " + file);
        var first = DeckImporter.ImportDeck(Path.GetFullPath(args[2]), Path.Combine(root, "first"));
        if (!first.Success) throw new InvalidDataException(first.ErrorMessage);
        var custom = first.ImportedDeck.Pages.SelectMany(page => page.Controls).Single(control => control.Config is MCCustomConfig);
        CheckControl(custom, applet.Manifest.AppletId);
        string exported = DeckResourceHelper.ExportDeck(first.ImportedDeck.Id, false, Path.Combine(root, "first"), Path.Combine(root, "exports"));
        var second = DeckImporter.ImportDeck(exported, Path.Combine(root, "second"));
        if (!second.Success) throw new InvalidDataException(second.ErrorMessage);
        var reimported = second.ImportedDeck.Pages.SelectMany(page => page.Controls).Single(control => control.Config is MCCustomConfig);
        CheckControl(reimported, applet.Manifest.AppletId);
        Console.WriteLine("PASS: isolated native .mapl import and .deck import/export/reimport; no actions executed.");
    }

    /// <summary>Verifies container identity, parameter overrides and serialized custom-event action data.</summary>
    private static void CheckControl(MatricControl control, string identity) {
        var config = (MCCustomConfig)control.Config;
        if (config.AppletId != identity || !config.AllowInteraction || config.AllowedFeatures != ""
            || config.AppletParams["SignalVariable"].ToString() != "skill_demo_signal")
            throw new InvalidDataException("Applet identity or container parameters changed.");
        if (control.ControlEvents.Count != 1 || control.ControlEvents[0].Name != "select-sample" || control.ControlEvents[0].Actions.Count != 1)
            throw new InvalidDataException("Custom event/action configuration changed.");
        var action = control.ControlEvents[0].Actions[0] as ActionSetServerVariableConfig;
        if (action == null || action.VariableName != "skill_demo_selection" || !action.VariableCalculateValueFunction.Contains("eventData.value"))
            throw new InvalidDataException("Applet event calculation was lost.");
    }
}
