import {
  PageContainer,
  PageHeader,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Badge,
  Button,
  Canvas3DContainer,
} from "../components/ui"
import { ArrowUpRight, Terminal, Layers } from "lucide-react"

export interface PlaceholderPageProps {
  eyebrow?: string
  title: string
  description: string
  endpointHint?: string
  features?: string[]
}

export function PlaceholderPage({
  eyebrow = "Foundation",
  title,
  description,
  endpointHint,
  features = [],
}: PlaceholderPageProps) {
  return (
    <PageContainer>
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="primary" withDot pulse>
              Foundation Ready
            </Badge>
          </div>
        }
      />

      {/* Grid of Foundation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Architecture Status</CardTitle>
              <Badge variant="success" withDot>
                Active Shell
              </Badge>
            </div>
            <CardDescription>
              Frontend foundation verified. API client bindings and domain views will attach in the next development phase.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <span className="text-xs font-mono font-medium text-muted-foreground uppercase tracking-wider">
                Target Backend Endpoint
              </span>
              <div className="flex items-center justify-between p-3 rounded bg-surface-base border border-border text-xs font-mono">
                <span className="text-foreground">{endpointHint || "/api/v1"}</span>
                <span className="text-muted-foreground">FastAPI REST</span>
              </div>
            </div>

            {features.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="text-xs font-mono font-medium text-muted-foreground uppercase tracking-wider">
                  Planned Domain Capabilities
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {features.map((feat) => (
                    <div
                      key={feat}
                      className="flex items-center gap-2 p-2.5 rounded bg-surface-base border border-border/70 text-xs text-foreground font-sans"
                    >
                      <Terminal className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
          <CardFooter>
            <span>ORQ Control Plane Foundation</span>
            <span className="font-mono text-[11px]">Phase: Frontend Foundation</span>
          </CardFooter>
        </Card>

        {/* 3D Depth Viewport Container */}
        <Canvas3DContainer className="min-h-[220px] p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
              <Layers className="h-4 w-4 text-primary" />
              <span>3D Viewport</span>
            </div>
            <Badge variant="outline" size="sm">
              GPU Ready
            </Badge>
          </div>

          <div className="space-y-1.5 my-auto py-4">
            <p className="text-xs font-mono text-foreground font-medium">
              Subtle Spatial Depth
            </p>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Perspective architecture primed for future restrained WebGL infrastructure visualizations.
            </p>
          </div>

          <Button
            variant="outline"
            size="xs"
            className="w-full justify-between font-mono"
            rightIcon={<ArrowUpRight className="h-3 w-3" />}
            onClick={() => window.open("https://github.com", "_blank")}
          >
            Documentation
          </Button>
        </Canvas3DContainer>
      </div>
    </PageContainer>
  )
}
