EduTrack is an application for managing student performances. Every teacher can create a test, quiz and assign it to students of group. Student can perform test and quiz, and get results. EduTrack is a web application, so it can be used on any device. It can be used by teachers and students. Users will be student, teacher and admin. Admin can manage teachers, students and tests. Teacher can create tests, quiz and assign them to students. Student can perform tests and quiz, and get results. Student can access to the test by link. Link can be active within specific period (managed by teacher). Student can leave the test by link, and test will be finished rapidly with result as 0 or Fail. Teacher can see the results of student. There should be fullscreen mode automatically activated and after 3 times of leaving the test, test will be finished rapidly with result as 0 or Fail. Every try of leaving the test should be logged and caused decrease of minutes of the test. Teachers can only see results of students of their group. Every student can only see results of themseslves. Admin can see results of all students. 

Features:
- Create test
- Create quiz
- Assign test to students
- Perform test
- Perform quiz
- Get results
- Fullscreen mode
- Tests
- 
Task for Today:
1. Implement Alembic migrations to FastAPI
2. Create Basic Student Performance checker application
3. Develope full screen only mode
4. Develop violation checking mode (if student leaves full_screen mode > 3 times, test finished rapidly with result as 0 or Fail)
5. Student can access to the test by link
6. Link can be active within specific period (managed by teacher)


⚠️ JWT authentication uses HS256 instead of the documented RS256, which is fine for development
❌ FastAPI-Mail and MinIO client are missing — their implementations are just stubs
⚠️ The admin permission check is stricter than documented — it only allows the "admin" role, but the docs indicate admins should have all teacher capabilities too




PS D:\lessons\python\edu-track> cd d:\lessons\python\edu-track\frontend ; bun add react-router-dom@latest zustand @tanstack/react-query @tanstack/react-query-devtools axios react-hook-form @hookform/resolvers zod recharts socket.io-client react-icons sass react-beautiful-dnd @hello-pangea/dnd react-hot-toast date-fns
bun add v1.3.10 (30e609e0)
warn: incorrect peer dependency "react@19.2.4"     

warn: incorrect peer dependency "react-dom@19.2.4" 

warn: incorrect peer dependency "react@19.2.4"     

warn: incorrect peer dependency "react@19.2.4"     

installed react-router-dom@7.13.1
installed zustand@5.0.11
installed @tanstack/react-query@5.90.21
installed @tanstack/react-query-devtools@5.91.3    
installed axios@1.13.6
installed react-hook-form@7.71.2
installed @hookform/resolvers@5.2.2
installed zod@4.3.6
installed recharts@3.7.0
installed socket.io-client@4.8.3
installed react-icons@5.6.0
installed sass@1.97.3 with binaries:
 - sass
installed react-beautiful-dnd@13.1.1
installed @hello-pangea/dnd@18.0.1
installed react-hot-toast@2.6.0
installed date-fns@4.1.0

108 packages installed [99.08s]

Blocked 1 postinstall. Run `bun pm untrusted` for details.
PS D:\lessons\python\edu-track\frontend> bun pm untrusted
bun pm untrusted v1.3.10 (30e609e0)

.\node_modules\@parcel\watcher @2.5.6
 » [install]: node scripts/build-from-source.js    

These dependencies had their lifecycle scripts blocked during install.

If you trust them and wish to run their scripts, use `bun pm trust`.
PS D:\lessons\python\edu-track\frontend> bun pm trust --all
bun pm trust v1.3.10 (30e609e0)

.\node_modules\@parcel\watcher @2.5.6
 ✓ [install]: node scripts/build-from-source.js    

 1 script ran across 1 package [466.00ms]
PS D:\lessons\python\edu-track\frontend> 

FIx those warnings.


You were doing admin module (users/groups) tasks.
After it there was, Admin analytics + reports
Teacher assessments + questions
Teacher results + analytics
Student take + proctoring SDK