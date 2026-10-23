using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using EXM.MatricPro;
using EXM.MatricPro.Actions;
using EXM.MatricPro.Controls;
using EXM.MatricPro.Controls.ControlDefinition;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

/// <summary>Exports offline authoring metadata from a built MATRIC assembly without executing actions.</summary>
internal static class ExportMatricCatalog {
    /// <summary>Builds a portable description of a serialized property and its nested value types.</summary>
    private static JObject Describe(Type type, JToken example, int depth = 0) {
        var nullable = Nullable.GetUnderlyingType(type);
        if (nullable != null) type = nullable;
        var result = new JObject { ["nullable"] = nullable != null || !type.IsValueType };
        if (type.IsEnum) {
            bool strings = example != null && example.Type == JTokenType.String;
            if (example == null || example.Type == JTokenType.Null) strings = JToken.FromObject(Enum.GetValues(type).GetValue(0)).Type == JTokenType.String;
            result["type"] = strings ? "string" : "integer";
            result["enum"] = strings ? new JArray(Enum.GetNames(type)) : new JArray(Enum.GetValues(type).Cast<object>().Select(Convert.ToInt64));
            result["enum_names"] = new JObject(Enum.GetNames(type).Select(name => new JProperty(name, Convert.ToInt64(Enum.Parse(type, name)))));
        } else if (type == typeof(string) || type == typeof(Guid)) result["type"] = "string";
        else if (type == typeof(bool)) result["type"] = "boolean";
        else if (new[] { typeof(int), typeof(long), typeof(short), typeof(byte), typeof(uint), typeof(ushort), typeof(ulong) }.Contains(type)) result["type"] = "integer";
        else if (new[] { typeof(float), typeof(double), typeof(decimal) }.Contains(type)) result["type"] = "number";
        else if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(List<>)) {
            result["type"] = "array";
            result["items"] = Describe(type.GetGenericArguments()[0], null, depth + 1);
        } else if (type == typeof(object) || typeof(IDictionary).IsAssignableFrom(type) || depth > 4) result["type"] = "any";
        else {
            result["type"] = "object";
            result["properties"] = Properties(type, example as JObject, depth + 1);
        }
        return result;
    }

    /// <summary>Describes writable configuration fields, retaining their actual JSON enum representation.</summary>
    private static JObject Properties(Type type, JObject example, int depth = 0) {
        var result = new JObject();
        foreach (var property in type.GetProperties().Where(p => p.CanWrite && p.GetIndexParameters().Length == 0).OrderBy(p => p.Name)) {
            result[property.Name] = Describe(property.PropertyType, example == null ? null : example[property.Name], depth);
        }
        foreach (var field in type.GetFields(BindingFlags.Public | BindingFlags.Instance).Where(f => !f.IsInitOnly).OrderBy(f => f.Name)) {
            result[field.Name] = Describe(field.FieldType, example == null ? null : example[field.Name], depth);
        }
        return result;
    }

    /// <summary>Removes runtime type strings and computed resource indexes from a JSON template.</summary>
    private static void Clean(JToken token) {
        if (token is JObject) {
            ((JObject)token).Remove("ActionType");
            ((JObject)token).Remove("FileResources");
        }
        foreach (var child in token.Children().ToList()) Clean(child);
    }

    /// <summary>Writes configuration templates, event compatibility and field metadata to the requested JSON file.</summary>
    private static void Main(string[] args) {
        var controls = new JObject();
        var actions = new JObject();
        var assembly = typeof(Deck).Assembly;
        foreach (var type in assembly.GetTypes().Where(t => !t.IsAbstract && typeof(IMatricControlDef).IsAssignableFrom(t)).OrderBy(t => t.Name)) {
            var definition = (IMatricControlDef)Activator.CreateInstance(type);
            var template = JObject.FromObject(new MatricControl(type));
            Clean(template);
            var events = new JObject();
            foreach (var e in definition.EventsDefinition) {
                events[e.Name] = new JObject(e.AllowedActions.Select(binding => new JProperty(binding.Action.ActionId, new JObject {
                    ["single"] = binding.Single, ["exclusive"] = binding.Exclusive, ["implicit"] = binding.Implicit
                })));
            }
            controls[type.Name] = new JObject {
                ["name"] = definition.DisplayName, ["description"] = definition.Description,
                ["template"] = template, ["events"] = events,
                ["properties"] = Properties(definition.ControlConfigType, (JObject)template["Config"])
            };
        }
        foreach (var action in ActionHelpers.AllActions.Values.OrderBy(a => a.ActionId)) {
            var template = JObject.FromObject(Activator.CreateInstance(action.ActionConfigType));
            Clean(template);
            actions[action.ActionId] = new JObject {
                ["name"] = action.DisplayName, ["description"] = action.Description,
                ["requires_implicit_release"] = action.RequiresImplicitRelease,
                ["template"] = template, ["properties"] = Properties(action.ActionConfigType, template)
            };
        }
        var keys = new JObject();
        var keyMap = (IDictionary)assembly.GetType("EXM.MatricPro.Actions.ActionExec.InputSimulatorHelper").GetField("Map").GetValue(null);
        foreach (DictionaryEntry key in keyMap) keys[(string)key.Key] = Convert.ToInt64(key.Value);
        var catalog = new JObject {
            ["deck_file_version"] = EXM.MatricPro.Util.Const.DECK_FILE_VERSION,
            ["source_commit"] = args[1], ["assembly_sha256"] = args[2],
            ["controls"] = controls, ["actions"] = actions, ["key_codes"] = keys
        };
        File.WriteAllText(args[0], catalog.ToString(Formatting.Indented).Replace("\r\n", "\n"));
        Console.WriteLine("Exported " + controls.Count + " controls and " + actions.Count + " actions.");
    }
}
