"use client";

import { useQuery, useMutation } from "convex/react";
import { api } from "../../../../convex/_generated/api";
import { visibilityRegistry, getSectionChildIds } from "@/lib/visibility-registry";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { useVisibilityPreview } from "@/contexts/VisibilityPreviewContext";

export default function AdminVisibility() {
  const config = useQuery(api.frontendConfig.getConfig);
  const setVisibility = useMutation(api.frontendConfig.setVisibility);
  const setSectionVisibility = useMutation(api.frontendConfig.setSectionVisibility);
  const { previewAsUser, togglePreview } = useVisibilityPreview();

  const overrides = config?.overrides ?? {};

  // Count visible items
  const allIds: string[] = [];
  for (const page of visibilityRegistry) {
    for (const section of page.sections) {
      allIds.push(section.id);
      for (const field of section.fields) {
        allIds.push(field.id);
      }
    }
  }
  const visibleCount = allIds.filter((id) => overrides[id] !== false).length;

  function isVisible(id: string): boolean {
    const parts = id.split(".");
    for (let i = 1; i <= parts.length; i++) {
      const ancestorId = parts.slice(0, i).join(".");
      if (overrides[ancestorId] === false) return false;
    }
    return true;
  }

  function isSectionOff(sectionId: string): boolean {
    return overrides[sectionId] === false;
  }

  async function handleSectionToggle(sectionId: string, checked: boolean) {
    const childIds = getSectionChildIds(sectionId);
    await setSectionVisibility({ sectionId, visible: checked, childIds });
  }

  async function handleFieldToggle(fieldId: string, checked: boolean) {
    await setVisibility({ id: fieldId, visible: checked });
  }

  if (config === undefined) {
    return <div className="text-muted-foreground text-sm">Loading configuration...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {visibleCount}/{allIds.length} elements visible
        </p>
        <button
          onClick={togglePreview}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
            previewAsUser
              ? "border-score-amber bg-score-amber/5 text-foreground"
              : "border-border bg-card text-muted-foreground hover:bg-muted"
          }`}
        >
          <span className={`inline-block h-2 w-2 rounded-full ${previewAsUser ? "bg-score-amber animate-pulse" : "bg-muted-foreground/40"}`} />
          {previewAsUser ? "Preview attiva — vedi come utente" : "Anteprima utente"}
        </button>
      </div>

      <Tabs defaultValue={visibilityRegistry[0].id}>
        <TabsList className="flex flex-wrap h-auto gap-1">
          {visibilityRegistry.map((page) => (
            <TabsTrigger key={page.id} value={page.id} className="text-xs">
              {page.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {visibilityRegistry.map((page) => (
          <TabsContent key={page.id} value={page.id} className="space-y-2 mt-4">
            {page.sections.map((section) => {
              const sectionOff = isSectionOff(section.id);

              return (
                <Collapsible key={section.id}>
                  <div className="flex items-center justify-between rounded-lg border border-border bg-card p-3">
                    <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                      <span className="text-muted-foreground">
                        {section.fields.length > 0 ? "▶" : "—"}
                      </span>
                      {section.label}
                      {section.fields.length > 0 && (
                        <span className="text-xs text-muted-foreground">
                          ({section.fields.length})
                        </span>
                      )}
                    </CollapsibleTrigger>
                    <Switch
                      checked={isVisible(section.id)}
                      onCheckedChange={(checked) =>
                        handleSectionToggle(section.id, checked)
                      }
                    />
                  </div>

                  {section.fields.length > 0 && (
                    <CollapsibleContent>
                      <div className="ml-6 mt-1 space-y-1">
                        {section.fields.map((field) => (
                          <div
                            key={field.id}
                            className={`flex items-center justify-between rounded border border-border/50 p-2 text-sm ${
                              sectionOff ? "opacity-40 pointer-events-none" : ""
                            }`}
                          >
                            <span className="text-muted-foreground">{field.label}</span>
                            <Switch
                              checked={isVisible(field.id)}
                              disabled={sectionOff}
                              onCheckedChange={(checked) =>
                                handleFieldToggle(field.id, checked)
                              }
                            />
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  )}
                </Collapsible>
              );
            })}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
