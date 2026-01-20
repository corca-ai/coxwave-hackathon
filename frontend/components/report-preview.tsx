import type { ReportOutput, VisualComponent, VisualOutput } from "../lib/types";

interface ReportPreviewProps {
  reportOutput: ReportOutput | null;
  visualOutput: VisualOutput | null;
}

function renderComponent(component: VisualComponent, index: number) {
  const props = component.props ?? {};
  switch (component.type) {
    case "heading": {
      const level = typeof props.level === "number" ? props.level : 1;
      const text = typeof props.text === "string" ? props.text : "";
      if (level <= 1) {
        return <h1 key={index}>{text}</h1>;
      }
      if (level === 2) {
        return <h2 key={index}>{text}</h2>;
      }
      return <h3 key={index}>{text}</h3>;
    }
    case "paragraph": {
      const text = typeof props.text === "string" ? props.text : "";
      return <p key={index}>{text}</p>;
    }
    case "bullets": {
      const items = Array.isArray(props.items) ? props.items : [];
      return (
        <ul key={index}>
          {items.map((item: unknown, itemIndex: number) => (
            <li key={itemIndex}>{String(item)}</li>
          ))}
        </ul>
      );
    }
    case "callout": {
      const title = typeof props.title === "string" ? props.title : undefined;
      const text = typeof props.text === "string" ? props.text : undefined;
      const items = Array.isArray(props.items) ? props.items : [];
      return (
        <div key={index} className="callout">
          {title ? <strong>{title}</strong> : null}
          {text ? <p>{text}</p> : null}
          {items.length > 0 ? (
            <ul>
              {items.map((item: unknown, itemIndex: number) => (
                <li key={itemIndex}>{String(item)}</li>
              ))}
            </ul>
          ) : null}
        </div>
      );
    }
    case "list": {
      const title = typeof props.title === "string" ? props.title : undefined;
      const items = Array.isArray(props.items) ? props.items : [];
      return (
        <div key={index}>
          {title ? <strong>{title}</strong> : null}
          <ul>
            {items.map((item: unknown, itemIndex: number) => (
              <li key={itemIndex}>{String(item)}</li>
            ))}
          </ul>
        </div>
      );
    }
    default:
      return (
        <pre key={index} className="json-block">
          {JSON.stringify(component, null, 2)}
        </pre>
      );
  }
}

export default function ReportPreview({ reportOutput, visualOutput }: ReportPreviewProps) {
  if (!visualOutput || !Array.isArray(visualOutput.components)) {
    if (!reportOutput) {
      return <div className="panel-subtitle">No report data loaded.</div>;
    }
    return (
      <div className="report-preview">
        <h2>{reportOutput.title}</h2>
        <p>{reportOutput.executive_summary}</p>
        <ul>
          {reportOutput.key_findings?.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="report-preview">
      {visualOutput.components.map((component, index) => renderComponent(component, index))}
    </div>
  );
}
