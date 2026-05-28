import React from "react";

interface SectionProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  id?: string;
}

const Section: React.FC<SectionProps> = ({ title, subtitle, children, id }) => {
  return (
    <section id={id} className="py-12 border-b border-gray-200">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-gray-900 mb-2">{title}</h2>
        {subtitle && <p className="text-lg text-gray-600 mb-6">{subtitle}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
};

export default Section;
