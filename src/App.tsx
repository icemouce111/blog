import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Layout } from '@/components/layout/Layout'
import { HomePage } from '@/pages/HomePage'
import { BlogPage } from '@/pages/BlogPage'
import { BlogPostPage } from '@/pages/BlogPostPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ResourcesPage } from '@/pages/ResourcesPage'
import { AboutPage } from '@/pages/AboutPage'
import { AiDailyPage } from '@/pages/AiDailyPage'
import { AiDailyPostPage } from '@/pages/AiDailyPostPage'
import { GithubPage } from '@/pages/GithubPage'
import { GithubPostPage } from '@/pages/GithubPostPage'

function App() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="blog" element={<BlogPage />} />
            <Route path="blog/:slug" element={<BlogPostPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="resources" element={<ResourcesPage />} />
            <Route path="about" element={<AboutPage />} />
            <Route path="ai-daily" element={<AiDailyPage />} />
            <Route path="ai-daily/:slug" element={<AiDailyPostPage />} />
            <Route path="github" element={<GithubPage />} />
            <Route path="github/:slug" element={<GithubPostPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  )
}

export default App
