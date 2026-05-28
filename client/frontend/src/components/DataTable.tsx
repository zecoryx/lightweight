import React from "react";

interface DataTableProps {
  headers: string[];
  rows: string[][];
}

const DataTable: React.FC<DataTableProps> = ({ headers, rows }) => {
  return (
    <div className="scrollbar-thin my-6 overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-[640px] divide-y divide-gray-200 sm:min-w-full">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((header, index) => (
              <th
                key={index}
                scope="col"
                className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 sm:px-6"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="whitespace-nowrap px-4 py-4 font-mono text-sm text-gray-700 sm:px-6"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
